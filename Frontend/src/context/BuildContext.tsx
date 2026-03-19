'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Component, ComponentCategory } from '../data/mockData';
import { checkCompatibility, CompatibilityReport } from '../services/api';

interface BuildState {
  [category: string]: Component | null;
}

interface BuildContextType {
  build: BuildState;
  totalPrice: number;
  totalWattage: number;
  compatibility: CompatibilityReport;
  addComponent: (component: Component) => void;
  replaceBuild: (components: Component[]) => void;
  removeComponent: (category: ComponentCategory) => void;
  clearBuild: () => void;
  checkBuildCompatibility: () => Promise<void>;
  isLoadingCompatibility: boolean;
}

const BuildContext = createContext<BuildContextType | undefined>(undefined);

const createInitialBuildState = (): BuildState => ({
  'CPU': null,
  'CPU Cooler': null,
  'Motherboard': null,
  'Memory': null,
  'Storage': null,
  'Video Card': null,
  'Case': null,
  'Power Supply': null,
});

export const BuildProvider = ({ children }: { children: ReactNode }) => {
  const [build, setBuild] = useState<BuildState>(createInitialBuildState);

  const [compatibility, setCompatibility] = useState<CompatibilityReport>({
    isValid: true,
    warnings: [],
    errors: [],
  });
  const [isLoadingCompatibility, setIsLoadingCompatibility] = useState(false);

  // Compute derived state
  const components = Object.values(build).filter(Boolean) as Component[];
  const totalPrice = components.reduce((sum, item) => sum + (item.price || 0), 0);
  const totalWattage = components.reduce((sum, item) => sum + (item.wattage || 0), 0);

  const checkBuildCompatibility = async () => {
    setIsLoadingCompatibility(true);
    try {
      const report = await checkCompatibility(components);
      setCompatibility(report);
    } catch (error) {
      console.error("Failed to check compatibility:", error);
    } finally {
      setIsLoadingCompatibility(false);
    }
  };

  // Re-check compatibility whenever build changes
  useEffect(() => {
    checkBuildCompatibility();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [build]);

  const addComponent = (component: Component) => {
    setBuild((prev) => ({
      ...prev,
      [component.category]: component,
    }));
  };

  const replaceBuild = (components: Component[]) => {
    const nextBuild = createInitialBuildState();

    for (const component of components) {
      nextBuild[component.category] = component;
    }

    setBuild(nextBuild);
  };

  const removeComponent = (category: ComponentCategory) => {
    setBuild((prev) => ({
      ...prev,
      [category]: null,
    }));
  };

  const clearBuild = () => {
    setBuild(createInitialBuildState());
  };

  return (
    <BuildContext.Provider
      value={{
        build,
        totalPrice,
        totalWattage,
        compatibility,
        addComponent,
        replaceBuild,
        removeComponent,
        clearBuild,
        checkBuildCompatibility,
        isLoadingCompatibility,
      }}
    >
      {children}
    </BuildContext.Provider>
  );
};

export const useBuild = () => {
  const context = useContext(BuildContext);
  if (context === undefined) {
    throw new Error('useBuild must be used within a BuildProvider');
  }
  return context;
};
