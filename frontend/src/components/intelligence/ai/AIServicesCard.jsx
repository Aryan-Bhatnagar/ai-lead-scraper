import React from 'react';

const AIServicesCard = ({ services }) => {
  if (!services || (Array.isArray(services) && services.length === 0)) return null;

  const servicesList = Array.isArray(services)
    ? services
    : JSON.parse(services || '[]');

  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
        Services Offered
      </h3>
      <div className="flex flex-wrap gap-2">
        {servicesList.map((service, idx) => (
          <span key={idx} className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-800">
            {service}
          </span>
        ))}
      </div>
    </div>
  );
};

export default AIServicesCard;
