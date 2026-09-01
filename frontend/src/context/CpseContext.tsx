import React, { createContext, useContext, useState } from 'react';
import type { CPSE } from '../types/api';

interface CpseContextType {
  selectedCpse: CPSE | null;
  setSelectedCpse: (cpse: CPSE | null) => void;
}

const CpseContext = createContext<CpseContextType | undefined>(undefined);

export const CpseProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedCpse, setSelectedCpse] = useState<CPSE | null>(null);

  return (
    <CpseContext.Provider value={{ selectedCpse, setSelectedCpse }}>
      {children}
    </CpseContext.Provider>
  );
};

export const useCpse = (): CpseContextType => {
  const context = useContext(CpseContext);
  if (!context) {
    throw new Error('useCpse must be used within a CpseProvider');
  }
  return context;
};
