import React, { useState } from 'react';
import { Tabs } from '../../components';
import { SuggestionQueue } from './suggestion-queue';
import { PolicyEditor } from './policy-editor';
import { ProcessingHistory } from './processing-history';
import { BackupManager } from './backup-manager';

export type SynonymTab = 'queue' | 'editor' | 'backup';

export const SynonymsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('queue');
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const handleGlobalRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const tabs = [
    { id: 'queue', label: 'Review Queue' },
    { id: 'editor', label: 'Policy Editors' },
    { id: 'backup', label: 'Backup & Restore' },
  ];

  return (
    <div className='content-container synonym-management-page' style={{ paddingBottom: 48 }}>
      {/* Header */}
      <div className='page-head' style={{ marginBottom: 24 }}>
        <p
          className='eyebrow'
          style={{
            color: 'var(--accent)',
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            margin: '0 0 6px',
          }}
        >
          Knowledge Base
        </p>
        <h2
          style={{
            margin: 0,
            fontFamily: 'var(--display-font)',
            fontSize: 26,
            letterSpacing: '-0.03em',
          }}
        >
          Taxonomy & Synonyms
        </h2>
        <p style={{ margin: '6px 0 0', color: 'var(--muted)', fontSize: 13 }}>
          Manage global skill, domain, and role-family normalization policies, triage proposals, and manage backups.
        </p>
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
              <SuggestionQueue key={'queue-' + refreshTrigger} onQueueChanged={handleGlobalRefresh} />
              <ProcessingHistory key={'history-' + refreshTrigger} />
            </div>
          )}
          {activeTab === 'editor' && (
            <PolicyEditor key={'editor-' + refreshTrigger} onPolicyUpdated={handleGlobalRefresh} />
          )}
          {activeTab === 'backup' && (
            <BackupManager key={'backup-' + refreshTrigger} onBackupImported={handleGlobalRefresh} />
          )}
        </div>
      </Tabs>
    </div>
  );
};

export default SynonymsPage;
