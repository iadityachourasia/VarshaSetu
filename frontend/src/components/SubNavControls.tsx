import React from 'react';
import { ScientificOutputUnavailable } from './ScientificOutputUnavailable';

export const SubNavControls: React.FC<Record<string, unknown>> = () => (
  <ScientificOutputUnavailable title="Analysis controls are disabled" />
);
