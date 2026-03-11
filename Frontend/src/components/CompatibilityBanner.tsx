'use client';

import React from 'react';
import { useBuild } from '@/context/BuildContext';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

export default function CompatibilityBanner() {
  const { compatibility, isLoadingCompatibility } = useBuild();

  if (isLoadingCompatibility) {
    return (
      <div className="w-full p-4 rounded-lg bg-mid-gray border border-border-gray flex items-center justify-center text-gray-400 animate-pulse">
        Checking compatibility...
      </div>
    );
  }

  const hasErrors = compatibility.errors.length > 0;
  const hasWarnings = compatibility.warnings.length > 0;

  if (!hasErrors && !hasWarnings && compatibility.isValid) {
    return (
      <div className="w-full p-4 rounded-lg bg-neon-green/10 border border-neon-green/30 flex items-start gap-3">
        <CheckCircle className="w-5 h-5 text-neon-green flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-neon-green">Compatibility OK</h4>
          <p className="text-sm text-gray-300 mt-1">All selected components appear to be compatible.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`w-full p-4 rounded-lg flex flex-col gap-3 ${hasErrors ? 'bg-red-500/10 border border-red-500/30' : 'bg-yellow-500/10 border border-yellow-500/30'}`}>
      
      {hasErrors && (
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-red-500">Incompatible Parts Component</h4>
            <ul className="list-disc list-inside text-sm text-gray-300 mt-1 space-y-1">
              {compatibility.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {hasWarnings && (
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-yellow-500">Compatibility Warnings</h4>
            <ul className="list-disc list-inside text-sm text-gray-300 mt-1 space-y-1">
              {compatibility.warnings.map((warn, i) => (
                <li key={i}>{warn}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

    </div>
  );
}
