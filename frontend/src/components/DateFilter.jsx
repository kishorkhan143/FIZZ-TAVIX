import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useDateFilter, formatDisplayDate, getLocalDateString } from '../dateFilterUtils';

export default function DateFilter() {
  const { selectedDate, setSelectedDate, today, isToday, resetToToday, displayDate } = useDateFilter();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Parse currently selected date or today into year and month for calendar navigation
  const initialDate = selectedDate ? new Date(`${selectedDate}T00:00:00`) : new Date(`${today}T00:00:00`);
  const [viewYear, setViewYear] = useState(initialDate.getFullYear() || 2026);
  const [viewMonth, setViewMonth] = useState(initialDate.getMonth() || 9); // 0-indexed

  // Close calendar when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // When selectedDate changes externally, sync viewMonth/viewYear
  useEffect(() => {
    if (selectedDate) {
      const d = new Date(`${selectedDate}T00:00:00`);
      if (!isNaN(d.getTime())) {
        setViewYear(d.getFullYear());
        setViewMonth(d.getMonth());
      }
    }
  }, [selectedDate]);

  const handlePrevMonth = (e) => {
    e.stopPropagation();
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(viewYear - 1);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const handleNextMonth = (e) => {
    e.stopPropagation();
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(viewYear + 1);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  // Month names
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

  // Calculate calendar grid
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstDayIndex = new Date(viewYear, viewMonth, 1).getDay(); // 0 is Sunday
  const daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

  const calendarDays = [];
  // Previous month trailing days
  for (let i = firstDayIndex - 1; i >= 0; i--) {
    calendarDays.push({
      day: daysInPrevMonth - i,
      month: viewMonth - 1,
      year: viewMonth === 0 ? viewYear - 1 : viewYear,
      isCurrentMonth: false,
    });
  }
  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    calendarDays.push({
      day: d,
      month: viewMonth,
      year: viewYear,
      isCurrentMonth: true,
    });
  }
  // Next month leading days to complete grid (up to multiple of 7)
  const remainingCells = 7 - (calendarDays.length % 7);
  if (remainingCells < 7) {
    for (let d = 1; d <= remainingCells; d++) {
      calendarDays.push({
        day: d,
        month: viewMonth + 1,
        year: viewMonth === 11 ? viewYear + 1 : viewYear,
        isCurrentMonth: false,
      });
    }
  }

  const formatIso = (y, m, d) => {
    const mm = String(m + 1).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    return `${y}-${mm}-${dd}`;
  };

  const handleSelectDay = (cell) => {
    const iso = formatIso(cell.year, cell.month, cell.day);
    if (iso > today) return; // Future dates disabled
    setSelectedDate(iso);
    setIsOpen(false);
  };

  const handlePreset = (type) => {
    if (type === 'today') {
      resetToToday();
    } else if (type === 'yesterday') {
      const d = new Date(`${today}T00:00:00`);
      d.setDate(d.getDate() - 1);
      setSelectedDate(getLocalDateString(d));
    } else if (type === '7days') {
      const d = new Date(`${today}T00:00:00`);
      d.setDate(d.getDate() - 7);
      setSelectedDate(getLocalDateString(d));
    }
    setIsOpen(false);
  };

  return (
    <div className="date-filter-container" ref={containerRef} style={{ position: 'relative' }}>
      {/* Date Filter Pill Button */}
      <div
        className={`date-filter-pill ${isOpen ? 'active-open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Click to open calendar"
        tabIndex={0}
        role="button"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
      >
        <span className="date-filter-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </span>
        <span className="date-filter-text">{displayDate}</span>
        <span className={`date-filter-chevron ${isOpen ? 'rotate' : ''}`}>▾</span>
      </div>

      {!isToday && (
        <button
          type="button"
          className="date-filter-today-btn"
          onClick={resetToToday}
          title="Reset filter to today"
        >
          Today
        </button>
      )}

      {/* Custom Themed iOS Floating Calendar Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="app-calendar-dropdown"
            initial={{ opacity: 0, y: -12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 420, damping: 28 }}
          >
            {/* Calendar Navigation Header */}
            <div className="cal-header">
              <button
                type="button"
                className="cal-nav-btn"
                onClick={handlePrevMonth}
                title="Previous Month"
              >
                ‹
              </button>
              <div className="cal-month-title">
                {monthNames[viewMonth]} {viewYear}
              </div>
              <button
                type="button"
                className="cal-nav-btn"
                onClick={handleNextMonth}
                title="Next Month"
              >
                ›
              </button>
            </div>

            {/* Day of Week Headers */}
            <div className="cal-weekdays">
              {dayNames.map((name) => (
                <div key={name} className="cal-weekday-label">
                  {name}
                </div>
              ))}
            </div>

            {/* Days Grid */}
            <div className="cal-grid">
              {calendarDays.map((cell, idx) => {
                const iso = formatIso(cell.year, cell.month, cell.day);
                const isSelected = iso === selectedDate;
                const isTodayDate = iso === today;
                const isFuture = iso > today;

                let cellClass = 'cal-day-cell';
                if (!cell.isCurrentMonth) cellClass += ' other-month';
                if (isSelected) cellClass += ' selected';
                if (isTodayDate) cellClass += ' today';
                if (isFuture) cellClass += ' disabled';

                return (
                  <button
                    key={`${iso}-${idx}`}
                    type="button"
                    className={cellClass}
                    disabled={isFuture}
                    onClick={() => handleSelectDay(cell)}
                  >
                    <span>{cell.day}</span>
                    {isTodayDate && !isSelected && <span className="cal-today-dot" />}
                  </button>
                );
              })}
            </div>

            {/* Quick Presets */}
            <div className="cal-footer">
              <button
                type="button"
                className="cal-preset-btn"
                onClick={() => handlePreset('today')}
              >
                Today
              </button>
              <button
                type="button"
                className="cal-preset-btn"
                onClick={() => handlePreset('yesterday')}
              >
                Yesterday
              </button>
              <button
                type="button"
                className="cal-preset-btn"
                onClick={() => handlePreset('7days')}
              >
                7 Days Ago
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
