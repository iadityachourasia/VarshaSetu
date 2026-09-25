import React from 'react';
import { ScientificOutputUnavailable } from './ScientificOutputUnavailable';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  units: 'metric' | 'imperial';
  setUnits: (value: 'metric' | 'imperial') => void;
  tempUnit: 'C' | 'F';
  setTempUnit: (value: 'C' | 'F') => void;
  exceedanceThreshold: number;
  setExceedanceThreshold: (value: number) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen }) => (
  isOpen ? <ScientificOutputUnavailable title="Scientific display settings are disabled" /> : null
);
