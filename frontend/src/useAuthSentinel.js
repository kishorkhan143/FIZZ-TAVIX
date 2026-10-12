/**
 * AuthSentinel — WebSocket + API Hook
 *
 * Connects to the backend WebSocket for real-time events/alerts.
 * Also provides REST fetch helpers.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getLocalDateString } from './dateFilterUtils';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:8000`;
const WS_URL      = import.meta.env.VITE_WS_URL      || `ws://${window.location.hostname}:8000/ws`;
const MAX_EVENTS  = 200;
const MAX_ALERTS  = 50;

export const parseUtc = (ts) => {
  if (!ts) return null;
  const s = String(ts);
  return new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(s) ? s : s + 'Z');
};

export const formatDateTime = (ts) => {
  if (!ts) return '—';
  try {
    const d = parseUtc(ts);
    if (!d || isNaN(d.getTime())) return '—';
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
  } catch {
    return String(ts);
  }
};

export function useAuthSentinel(selectedDate) {
  const [events, setEvents]         = useState([]);
  const [alerts, setAlerts]         = useState([]);
  const [labs, setLabs]             = useState([]);
  const [terminals, setTerminals]   = useState([]);
  const [labHours, setLabHours]     = useState({ start_time: '09:00', end_time: '18:00', is_open: true, status: 'USUAL' });
  const [stats, setStats]           = useState({
    total_events: 0,
    successful_logins: 0,
    failed_logins: 0,
    active_alerts: 0,
    critical_alerts: 0,
    high_alerts: 0,
    active_incidents: 0,
    resolved_incidents: 0,
  });
  const [health, setHealth]         = useState(null);
  const [wsStatus, setWsStatus]     = useState('CONNECTING');  // CONNECTING | CONNECTED | DISCONNECTED
  const [toasts, setToasts]         = useState([]);
  const [isLoading, setIsLoading]   = useState(true);

  const wsRef          = useRef(null);
  const reconnectRef   = useRef(null);
  const reconnectCount = useRef(0);
  const selectedDateRef = useRef(selectedDate);

  useEffect(() => {
    selectedDateRef.current = selectedDate;
  }, [selectedDate]);

  // ── REST helpers ────────────────────────────────────────────
  const fetchInitialData = useCallback(async (dateFilter = selectedDateRef.current) => {
    setIsLoading(true);
    try {
      const todayStr = getLocalDateString();
      const isHistorical = dateFilter && dateFilter !== todayStr;
      const eventsUrl = isHistorical
        ? `${BACKEND_URL}/api/events?limit=200&date=${dateFilter}`
        : `${BACKEND_URL}/api/events?limit=200`;
      const alertsUrl = isHistorical
        ? `${BACKEND_URL}/api/alerts?limit=100&date=${dateFilter}`
        : `${BACKEND_URL}/api/alerts?limit=100`;

      const [eventsRes, alertsRes, statsRes, healthRes, labsRes, terminalsRes, labHoursRes] = await Promise.all([
        fetch(eventsUrl),
        fetch(alertsUrl),
        fetch(`${BACKEND_URL}/api/stats`),
        fetch(`${BACKEND_URL}/api/health`),
        fetch(`${BACKEND_URL}/api/labs`),
        fetch(`${BACKEND_URL}/api/terminals`),
        fetch(`${BACKEND_URL}/api/lab-hours`),
      ]);
      if (eventsRes.ok) setEvents(await eventsRes.json());
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (statsRes.ok)  setStats(await statsRes.json());
      if (healthRes.ok) setHealth(await healthRes.json());
      if (labsRes.ok)   setLabs(await labsRes.json());
      if (terminalsRes.ok) setTerminals(await terminalsRes.json());
      if (labHoursRes?.ok) setLabHours(await labHoursRes.json());
    } catch (err) {
      console.warn('Initial fetch failed:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshStats = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/stats`);
      if (res.ok) setStats(await res.json());
    } catch (_) {}
  }, []);

  const refreshHealth = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) setHealth(await res.json());
    } catch (_) {}
  }, []);

  const refreshLabs = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/labs`);
      if (res.ok) setLabs(await res.json());
    } catch (_) {}
  }, []);

  const refreshTerminals = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/terminals`);
      if (res.ok) setTerminals(await res.json());
    } catch (_) {}
  }, []);

  // ── Actions ──────────────────────────────────────────────────
  const updateAlertStatus = useCallback(async (alertId, newStatus) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/alerts/${alertId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || `Failed to update alert status (${res.status})`);
      }
      const data = await res.json();
      setAlerts(prev =>
        prev.map(a => (a.id === alertId ? { ...a, status: data.status, resolved: data.resolved } : a))
      );
      refreshStats();
      return data;
    } catch (err) {
      console.warn('Failed to update alert status:', err);
      throw err;
    }
  }, [refreshStats]);

  const executeAlertAction = useCallback(async (alertId, action, options = {}) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/alerts/${alertId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          note: options.note,
          terminal_id: options.terminalId,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const alertStatus = action === 'authorize'
          ? data.status
          : data.alert_status || 'REMEDIATING';
        const resolved = alertStatus === 'AUTHORIZED';
        setAlerts(prev =>
          prev.map(a => (
            a.id === alertId
              ? { ...a, status: alertStatus, resolved }
              : a
          ))
        );
        refreshStats();
        return data;
      } else {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to execute action');
      }
    } catch (err) {
      console.warn('Action execution failed:', err);
      throw err;
    }
  }, [refreshStats]);

  const addLab = useCallback(async (labData) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/labs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(labData),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || `Failed to create laboratory (${res.status})`);
      }
      const created = await res.json();
      setLabs(prev => [created, ...prev]);
      return created;
    } catch (err) {
      console.warn('Failed to create laboratory:', err);
      throw err;
    }
  }, []);

  const deleteLab = useCallback(async (labId) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/labs/${labId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setLabs(prev => prev.filter(l => l.id !== labId));
        refreshTerminals();
      }
    } catch (err) {
      console.warn('Failed to delete lab:', err);
    }
  }, [refreshTerminals]);

  const updateLabHours = useCallback(async (startTime, endTime) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/lab-hours`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_time: startTime, end_time: endTime }),
      });
      if (res.ok) {
        const data = await res.json();
        setLabHours(data);
        return data;
      }
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to update lab hours (${res.status})`);
    } catch (err) {
      console.warn('Failed to update lab hours:', err);
      throw err;
    }
  }, []);

  const assignTerminal = useCallback(async (terminalId, labId) => {
    // Optimistic UI update
    const selectedLab = labs.find(l => l.id === labId);
    const previousTerminal = terminals.find(t => t.terminal_id === terminalId);
    setTerminals(prev =>
      prev.map(t =>
        t.terminal_id === terminalId
          ? { ...t, lab_id: labId, lab_name: selectedLab ? selectedLab.name : null }
          : t
      )
    );
    try {
      const res = await fetch(`${BACKEND_URL}/api/terminals/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ terminal_id: terminalId, lab_id: labId }),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || `Failed to assign terminal to laboratory (${res.status})`);
      }
      refreshLabs();
      refreshTerminals();
    } catch (err) {
      setTerminals(prev =>
        prev.map(t =>
          t.terminal_id === terminalId
            ? { ...t, lab_id: previousTerminal?.lab_id || null, lab_name: previousTerminal?.lab_name || null }
            : t
        )
      );
      console.warn('Failed to assign terminal:', err);
      throw err;
    }
  }, [labs, refreshLabs, refreshTerminals, terminals]);

  const exportLiveTelemetry = useCallback(() => {
    if (!events.length) {
      alert('No telemetry data available to export.');
      return;
    }
    window.location.href = `${BACKEND_URL}/api/telemetry/export`;
  }, [events]);

  // ── Toast management ─────────────────────────────────────────
  const addToast = useCallback((alert) => {
    const id = Date.now();
    setToasts(prev => [...prev, { ...alert, _toastId: id }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t._toastId !== id));
    }, 6000);
  }, []);

  // ── WebSocket ────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return;  // CONNECTING or OPEN

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    setWsStatus('CONNECTING');

    ws.onopen = () => {
      setWsStatus('CONNECTED');
      reconnectCount.current = 0;
      fetchInitialData();
      const ping = setInterval(() => {
        if (ws.readyState === 1) ws.send('ping');
      }, 25000);
      ws._pingInterval = ping;
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        handleMessage(msg);
      } catch (_) {}
    };

    ws.onclose = () => {
      setWsStatus('DISCONNECTED');
      if (ws._pingInterval) clearInterval(ws._pingInterval);
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [fetchInitialData]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectRef.current) return;
    const delay = Math.min(1000 * 2 ** reconnectCount.current, 30000);
    reconnectCount.current++;
    reconnectRef.current = setTimeout(() => {
      reconnectRef.current = null;
      connect();
    }, delay);
  }, [connect]);

  const handleMessage = useCallback((msg) => {
    const activeDate = selectedDateRef.current;
    const isLive = !activeDate || activeDate === getLocalDateString();

    switch (msg.type) {
      case 'NEW_EVENT':
        if (isLive) {
          setEvents(prev => {
            const exists = prev.some(e => e.id === msg.event.id);
            if (exists) return prev;
            return [{ ...msg.event, _new: true }, ...prev].slice(0, MAX_EVENTS);
          });
        }
        refreshStats();
        refreshTerminals();
        break;

      case 'NEW_ALERT':
        if (isLive) {
          setAlerts(prev => {
            const exists = prev.some(a => a.id === msg.alert.id);
            if (exists) return prev;
            return [{ ...msg.alert, _new: true }, ...prev].slice(0, MAX_ALERTS);
          });
        }
        addToast(msg.alert);
        refreshStats();
        break;

      case 'ALERT_STATUS_CHANGED':
        setAlerts(prev =>
          prev.map(a =>
            a.id === msg.alert.id
              ? { ...a, status: msg.alert.status, resolved: msg.alert.resolved }
              : a
          )
        );
        refreshStats();
        break;

      case 'ALERT_ACTION_EXECUTED':
        setAlerts(prev =>
          prev.map(a =>
            a.id === msg.alert_id || a.id === msg.alert?.id
              ? {
                  ...a,
                  status: msg.status || msg.alert?.status || a.status,
                  resolved: msg.resolved ?? msg.alert?.resolved ?? true,
                  reason: msg.alert?.reason || a.reason,
                }
              : a
          )
        );
        if (msg.message) {
          addToast({
            title: `Admin Action: ${msg.action ? msg.action.replace('_', ' ').toUpperCase() : 'VERIFIED'}`,
            message: msg.message,
            risk_level: msg.action === 'shutdown' ? 'HIGH' : msg.action === 'lock_screen' ? 'MEDIUM' : 'LOW',
          });
        }
        refreshStats();
        break;

      case 'COMMAND_DISPATCHED':
        addToast({
          title: `Command Dispatched: ${msg.command?.toUpperCase()}`,
          message: msg.message || `Command sent to ${msg.terminal_id}`,
          risk_level: 'HIGH',
        });
        break;

      case 'COMMAND_ACK':
        addToast({
          title: `Command Executed: ${msg.command?.toUpperCase()}`,
          message: `${msg.terminal_id}: ${msg.message}`,
          risk_level: 'LOW',
        });
        refreshTerminals();
        break;

      case 'TERMINAL_ASSIGNED':
        refreshTerminals();
        refreshLabs();
        break;

      case 'LAB_HOURS_UPDATED':
        if (msg.lab_hours) {
          setLabHours(msg.lab_hours);
        }
        break;

      case 'RESET':
        setEvents([]);
        setAlerts([]);
        setStats({
          total_events: 0,
          successful_logins: 0,
          failed_logins: 0,
          active_alerts: 0,
          critical_alerts: 0,
          high_alerts: 0,
          active_incidents: 0,
          resolved_incidents: 0,
        });
        setToasts([]);
        break;

      case 'COLLECTOR_STATUS':
        setHealth(prev => prev ? {
          ...prev,
          collector_status: msg.status,
          collector_hostname: msg.hostname,
          collector_ip: msg.ip,
        } : prev);
        break;

      default:
        break;
    }
  }, [refreshStats, refreshTerminals, refreshLabs, addToast]);

  useEffect(() => {
    const ws = wsRef.current;
    if (ws) {
      ws.onmessage = (evt) => {
        try { handleMessage(JSON.parse(evt.data)); } catch (_) {}
      };
    }
  }, [handleMessage]);

  useEffect(() => {
    if (selectedDate !== undefined) {
      fetchInitialData(selectedDate);
    }
  }, [selectedDate, fetchInitialData]);

  useEffect(() => {
    connect();
    const healthTimer = setInterval(refreshHealth, 10000);
    const dataTimer = setInterval(() => {
      refreshStats();
    }, 15000);
    return () => {
      clearInterval(healthTimer);
      clearInterval(dataTimer);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return {
    events,
    alerts,
    labs,
    terminals,
    stats,
    health,
    wsStatus,
    toasts,
    isLoading,
    updateAlertStatus,
    executeAlertAction,
    addLab,
    deleteLab,
    assignTerminal,
    labHours,
    updateLabHours,
    exportLiveTelemetry,
    refreshInitialData: fetchInitialData,
  };
}

export { BACKEND_URL };
