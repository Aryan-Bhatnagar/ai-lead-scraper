import React from 'react';
import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';

export default function ConfidenceBadge({ level }) {
  const config = {
    High: { icon: ShieldCheck, color: 'text-green-600 bg-green-50', label: 'High Confidence' },
    Medium: { icon: ShieldQuestion, color: 'text-amber-600 bg-amber-50', label: 'Medium Confidence' },
    Low: { icon: ShieldAlert, color: 'text-red-600 bg-red-50', label: 'Low Confidence' },
  };

  const { icon: Icon, color, label } = config[level] || config.Low;

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${color} text-[10px] font-bold uppercase tracking-wider`}>
      <Icon className="w-3 h-3" />
      {label}
    </div>
  );
}
