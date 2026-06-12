'use client';

import React, { createContext, useContext, useReducer, useEffect, useState } from 'react';
import type { BrandData } from '@/lib/api';
import { getPersona, savePersona } from '@/lib/api';
import { personaToBrandData } from '@/lib/api';

interface SchedulerState {
  currentBrandId: string | null;
  brandData: BrandData | null;
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;
}

type SchedulerAction =
  | { type: 'SET_BRAND_ID'; payload: string }
  | { type: 'SET_BRAND_DATA'; payload: BrandData | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_DEMO_MODE'; payload: boolean }
  | { type: 'CLEAR_BRAND' };

const initialState: SchedulerState = {
  currentBrandId: null,
  brandData: null,
  isLoading: false,
  error: null,
  isDemoMode: false,
};

function schedulerReducer(state: SchedulerState, action: SchedulerAction): SchedulerState {
  switch (action.type) {
    case 'SET_BRAND_ID':
      return { ...state, currentBrandId: action.payload };
    case 'SET_BRAND_DATA':
      return { ...state, brandData: action.payload, error: null };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    case 'SET_DEMO_MODE':
      return { ...state, isDemoMode: action.payload };
    case 'CLEAR_BRAND':
      return { ...initialState };
    default:
      return state;
  }
}

interface SchedulerContextType {
  state: SchedulerState;
  setBrandId: (brandId: string) => void;
  setBrandData: (data: BrandData | null) => void;
  saveBrandData: (data: BrandData) => Promise<void>;
  loadBrandData: (brandId: string) => Promise<void>;
  setDemoMode: (enabled: boolean) => void;
  clearBrand: () => void;
}

const SchedulerContext = createContext<SchedulerContextType | undefined>(undefined);

export function SchedulerProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(schedulerReducer, initialState);

  // Demo mode localStorage key for brand data
  const DEMO_STORAGE_KEY = 'scheduler_demo_brand_data';

  const setBrandId = (brandId: string) => {
    dispatch({ type: 'SET_BRAND_ID', payload: brandId });
  };

  const setBrandData = (data: BrandData | null) => {
    dispatch({ type: 'SET_BRAND_DATA', payload: data });
    
    // In demo mode, save to localStorage
    if (state.isDemoMode) {
      try {
        if (data) {
          localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(data));
        } else {
          localStorage.removeItem(DEMO_STORAGE_KEY);
        }
      } catch (error) {
        console.warn('Failed to save demo brand data to localStorage:', error);
      }
    }
  };

  const saveBrandData = async (data: BrandData) => {
    if (!state.currentBrandId) {
      dispatch({ type: 'SET_ERROR', payload: 'No brand selected' });
      return;
    }

    dispatch({ type: 'SET_LOADING', payload: true });
    
    try {
      if (state.isDemoMode) {
        // In demo mode, just update localStorage
        localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(data));
        dispatch({ type: 'SET_BRAND_DATA', payload: data });
      } else {
        // In authenticated mode, save to backend
        await savePersona(state.currentBrandId, data);
        dispatch({ type: 'SET_BRAND_DATA', payload: data });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save brand data';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      throw error;
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const loadBrandData = async (brandId: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_BRAND_ID', payload: brandId });
    
    try {
      if (state.isDemoMode) {
        // In demo mode, load from localStorage
        const stored = localStorage.getItem(DEMO_STORAGE_KEY);
        if (stored) {
          const data = JSON.parse(stored) as BrandData;
          dispatch({ type: 'SET_BRAND_DATA', payload: data });
        } else {
          // No demo data, set empty state
          dispatch({ type: 'SET_BRAND_DATA', payload: null });
        }
      } else {
        // In authenticated mode, load from backend
        const persona = await getPersona(brandId);
        if (persona) {
          const brandData = personaToBrandData(persona);
          dispatch({ type: 'SET_BRAND_DATA', payload: brandData });
        } else {
          // No persona found, set empty state
          dispatch({ type: 'SET_BRAND_DATA', payload: null });
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load brand data';
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const setDemoMode = (enabled: boolean) => {
    dispatch({ type: 'SET_DEMO_MODE', payload: enabled });
    
    // Clear any existing data when switching modes
    if (state.brandData) {
      dispatch({ type: 'SET_BRAND_DATA', payload: null });
    }
  };

  const clearBrand = () => {
    // Clear localStorage in demo mode
    if (state.isDemoMode) {
      try {
        localStorage.removeItem(DEMO_STORAGE_KEY);
      } catch (error) {
        console.warn('Failed to clear demo brand data from localStorage:', error);
      }
    }
    
    dispatch({ type: 'CLEAR_BRAND' });
  };

  const contextValue: SchedulerContextType = {
    state,
    setBrandId,
    setBrandData,
    saveBrandData,
    loadBrandData,
    setDemoMode,
    clearBrand,
  };

  return (
    <SchedulerContext.Provider value={contextValue}>
      {children}
    </SchedulerContext.Provider>
  );
}

export function useScheduler(): SchedulerContextType {
  const context = useContext(SchedulerContext);
  if (context === undefined) {
    throw new Error('useScheduler must be used within a SchedulerProvider');
  }
  return context;
}

// Hook for brand data with automatic loading
export function useBrandData(brandId?: string) {
  const { state, loadBrandData } = useScheduler();
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    if (brandId && brandId !== state.currentBrandId && !hasLoaded) {
      loadBrandData(brandId);
      setHasLoaded(true);
    }
  }, [brandId, state.currentBrandId, loadBrandData, hasLoaded]);

  return {
    brandData: state.brandData,
    isLoading: state.isLoading,
    error: state.error,
    isDemoMode: state.isDemoMode,
  };
}