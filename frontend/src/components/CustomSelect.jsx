import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { springs } from '../motion';
import './CustomSelect.css';

/**
 * CustomSelect - Styled dropdown matching TAVIX GUARD dashboard theme
 * Replaces native <select> with custom styled component
 */
export default function CustomSelect({
  value,
  onChange,
  options = [],
  placeholder = 'Select option...',
  label,
  disabled = false,
  className = '',
  style = {},
  ...props
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);
  const displayLabel = selectedOption?.label || placeholder;

  const handleSelect = (optionValue) => {
    onChange({ target: { value: optionValue } });
    setIsOpen(false);
  };

  return (
    <div className={`custom-select-wrapper ${className}`} ref={containerRef} style={style}>
      {label && (
        <label className="custom-select-label">{label}</label>
      )}
      
      <div className={`custom-select-container ${isOpen ? 'open' : ''} ${disabled ? 'disabled' : ''}`}>
        {/* Select Button */}
        <button
          type="button"
          className="custom-select-button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          disabled={disabled}
          {...props}
        >
          <span className="custom-select-value">{displayLabel}</span>
          <motion.svg
            className="custom-select-chevron"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={springs.snappy}
          >
            <polyline points="6 9 12 15 18 9" />
          </motion.svg>
        </button>

        {/* Dropdown Menu */}
        <AnimatePresence>
          {isOpen && !disabled && (
            <motion.div
              className="custom-select-menu"
              role="listbox"
              initial={{ opacity: 0, scaleY: 0.9, y: -4 }}
              animate={{ opacity: 1, scaleY: 1, y: 0 }}
              exit={{ opacity: 0, scaleY: 0.9, y: -4 }}
              transition={springs.sheet}
              style={{ transformOrigin: 'top center' }}
            >
            {/* Options List */}
            <div className="custom-select-options">
              {options.length === 0 ? (
                <div className="custom-select-empty">No options available</div>
              ) : (
                options.map((option, index) => (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    className={`custom-select-option ${value === option.value ? 'selected' : ''}`}
                    onClick={() => handleSelect(option.value)}
                    aria-selected={value === option.value}
                  >
                    <span className="option-dot"></span>
                    <span className="option-label">{option.label}</span>
                    {value === option.value && (
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        style={{ marginLeft: 'auto' }}
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                ))
              )}
            </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
