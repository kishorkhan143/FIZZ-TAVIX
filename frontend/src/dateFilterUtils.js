import React, { createContext, useContext, useState, useMemo, useCallback } from 'react';
import { parseUtc } from './useAuthSentinel';

export const TIMEZONE = 'Asia/Kolkata';

/**
 * Returns current date in Asia/Kolkata as 'YYYY-MM-DD'
 */
export function getLocalDateString(dateObj = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(dateObj);
}

/**
 * Formats 'YYYY-MM-DD' to 'DD Mon YYYY' (e.g. '08 Oct 2026')
 */
export function formatDisplayDate(isoDateStr) {
  if (!isoDateStr) return '';
  try {
    const [year, month, day] = isoDateStr.split('-').map(Number);
    const d = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: TIMEZONE,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(d);
  } catch {
    return isoDateStr;
  }
}

/**
 * Formats timestamp to HH:MM:SS in Asia/Kolkata
 */
export function fmtTime(ts) {
  if (!ts) return '—';
  try {
    const d = parseUtc(ts);
    if (!d || isNaN(d.getTime())) return '—';
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: TIMEZONE,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return String(ts);
  }
}

/**
 * Formats timestamp to dd/mm/yyyy, HH:MM:SS in Asia/Kolkata
 */
export function fmtDateTime(ts) {
  if (!ts) return '—';
  try {
    const d = parseUtc(ts);
    if (!d || isNaN(d.getTime())) return '—';
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: TIMEZONE,
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).formatToParts(d);

    const map = {};
    parts.forEach((p) => {
      map[p.type] = p.value;
    });
    return `${map.day}/${map.month}/${map.year}, ${map.hour}:${map.minute}:${map.second}`;
  } catch {
    return String(ts);
  }
}

/**
 * Extracts 'YYYY-MM-DD' in Asia/Kolkata from any timestamp string
 */
export function getItemDateString(ts) {
  if (!ts) return null;
  const d = parseUtc(ts);
  if (!d || isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d);
}

/**
 * Filters items whose timestamp falls on selectedDate (YYYY-MM-DD)
 */
export function filterByDate(
  items = [],
  selectedDate,
  getTimestamp = (it) => it.timestamp || it.triggered_at || it.created_at
) {
  if (!selectedDate || !Array.isArray(items)) return items;
  return items.filter((item) => {
    const ts = getTimestamp(item);
    if (!ts) return false;
    return getItemDateString(ts) === selectedDate;
  });
}

const DateContext = createContext(null);

export function DateProvider({ children }) {
  const today = useMemo(() => getLocalDateString(), []);
  
  // Initialize from URL param ?date=YYYY-MM-DD if valid, else today
  const [selectedDate, setSelectedDateState] = useState(() => {
    try {
      const param = new URLSearchParams(window.location.search).get('date');
      if (param && /^\d{4}-\d{2}-\d{2}$/.test(param) && param <= today) {
        return param;
      }
    } catch {
      // fallback
    }
    return today;
  });

  const setSelectedDate = useCallback((newDate) => {
    if (!newDate) return;
    setSelectedDateState(newDate);
    // sync to URL query parameter without full reload
    try {
      const url = new URL(window.location.href);
      if (newDate === today) {
        url.searchParams.delete('date');
      } else {
        url.searchParams.set('date', newDate);
      }
      window.history.replaceState({}, '', url.toString());
    } catch {
      // ignore in test environments
    }
  }, [today]);

  const isToday = selectedDate === today;

  const resetToToday = useCallback(() => {
    setSelectedDate(today);
  }, [setSelectedDate, today]);

  const displayDate = useMemo(() => formatDisplayDate(selectedDate), [selectedDate]);

  return React.createElement(
    DateContext.Provider,
    {
      value: {
        selectedDate,
        setSelectedDate,
        today,
        isToday,
        resetToToday,
        displayDate,
      },
    },
    children
  );
}

export function useDateFilter() {
  const ctx = useContext(DateContext);
  if (!ctx) {
    throw new Error('useDateFilter must be used within a DateProvider');
  }
  return ctx;
}
