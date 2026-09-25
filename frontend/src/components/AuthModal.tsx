import React from 'react';
import { ScientificOutputUnavailable } from './ScientificOutputUnavailable';

interface AuthModalProps {
  isOpen: boolean;
  initialMode?: 'login' | 'register' | 'forgot';
  onClose: () => void;
  onSuccess?: (user: { name: string; email: string; role: string }) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen }) => (
  isOpen ? <ScientificOutputUnavailable title="Authentication is not implemented" /> : null
);
