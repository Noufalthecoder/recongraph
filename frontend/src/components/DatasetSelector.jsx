import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, AlertCircle, Loader2 } from 'lucide-react';

export default function DatasetSelector({
  scenarios,
  activeScenarioId,
  onSelectScenario,
  isSwitching,
  scenarioError
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const activeScenario = scenarios?.find(s => s.scenario_id === activeScenarioId);

  const handleSelect = (id) => {
    if (id !== activeScenarioId && !isSwitching) {
      onSelectScenario(id);
    }
    setIsOpen(false);
  };

  return (
    <div className="dataset-selector-container" ref={dropdownRef}>
      <label className="dataset-selector-label">ACTIVE DATASET</label>
      
      <button 
        className={`dataset-selector-trigger ${isOpen ? 'open' : ''} ${scenarioError ? 'has-error' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSwitching}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="dataset-selector-value">
          {isSwitching ? (
            <span className="dataset-status loading">
              <Loader2 size={14} className="spin-icon" /> Switching dataset...
            </span>
          ) : activeScenario ? (
            <div className="dataset-active-info">
              <div className="dataset-name">{activeScenario.name}</div>
              <div className="dataset-meta">{activeScenario.description}</div>
            </div>
          ) : (
            <span className="dataset-placeholder">Select a dataset...</span>
          )}
        </div>
        <ChevronDown size={16} className={`dataset-chevron ${isOpen ? 'open' : ''}`} />
      </button>

      {scenarioError && (
        <div className="dataset-error-msg">
          <AlertCircle size={12} />
          {scenarioError}
        </div>
      )}

      {isOpen && (
        <div className="dataset-dropdown-menu" role="listbox">
          {scenarios?.map((scenario) => {
            const isSelected = scenario.scenario_id === activeScenarioId;
            return (
              <button
                key={scenario.scenario_id}
                role="option"
                aria-selected={isSelected}
                className={`dataset-option ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelect(scenario.scenario_id)}
              >
                <div className="dataset-option-check">
                  {isSelected && <Check size={16} />}
                </div>
                <div className="dataset-option-content">
                  <div className="dataset-option-name">{scenario.name}</div>
                  <div className="dataset-option-meta">
                    {scenario.record_count} records · {scenario.has_anomalies ? 'Contains anomalies' : 'Clean dataset'}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
