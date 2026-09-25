import React from 'react';
import { ScientificOutputUnavailable } from './ScientificOutputUnavailable';

export const NotificationsModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen }) => (
  isOpen ? <ScientificOutputUnavailable title="Notifications are not implemented" /> : null
);
