import React, { useState } from 'react';
import { Tabs } from '../../components';
import { SuggestionQueue } from './suggestion-queue';
import { PolicyEditor } from './policy-editor';
import { ProcessingHistory } from './processing-history';
import { BackupManager } from './backup-manager';

export type SynonymTab = 'queue' | 'editor' | 'backup';

export const SynonymsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('queue');
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState<number>(0);

  const handleGlobalRefresh = () => {
    setHistoryRefreshTrigger((prev) => prev + 1);
  };

  const tabs = [
    { id: 'queue', label: 'Review Queue' },
    { id: 'editor', label: 'Policy Editors' },
    { id: 'backup', label: 'Backup & Restore' },
  ];

  return (
    <div className='content-container synonym-management-page'>
      {/* Header */}
      <div className='page-head'>
        <div>
          <p className='eyebrow'>Knowledge Base</p>
          <h2>Taxonomy & Synonyms</h2>
          <p>Manage global skill, domain, and role-family normalization policies, triage proposals, and manage backups.</p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        items={tabs}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id)}
        ariaLabel='Synonym management sections'
      >
        <div style={{ marginTop: 20 }}>
          {activeTab === 'queue' && (
            <div style={{ display: 'grid', gap: 24 }}>
              <SuggestionQueue onQueueChanged={handleGlobalRefresh} />
              <ProcessingHistory refreshTrigger={historyRefreshTrigger} />
            </div>
          )}
          {activeTab === 'editor' && (
            <PolicyEditor />
          )}
          {activeTab === 'backup' && (
            <BackupManager />
          )}
        </div>
      </Tabs>
    </div>
  );
};

export default SynonymsPage;
