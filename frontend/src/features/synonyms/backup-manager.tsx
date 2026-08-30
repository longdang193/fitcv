import React, { useState, useRef } from 'react';
import { Button } from '../../components';
import { ApiClientError, apiClient } from '../../lib/api-client';
import { exportSynonymBackup, importSynonymBackup } from './api';

export interface BackupManagerProps {
  onBackupImported?: () => void;
}

export const BackupManager: React.FC<BackupManagerProps> = ({ onBackupImported }) => {
  const [exporting, setExporting] = useState<boolean>(false);
  const [importing, setImporting] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [expectedRevisionId, setExpectedRevisionId] = useState<string>('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExportZip = async () => {
    setExporting(true);
    setError(null);
    setFeedback(null);
    try {
      await exportSynonymBackup();
      setFeedback('Synonym backup archive downloaded successfully.');
    } catch (err: any) {
      const msg = err instanceof ApiClientError ? err.message : 'Failed to export backup archive.';
      setError(msg);
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadYaml = async (url: string, filename: string) => {
    try {
      await apiClient.download(url, filename);
    } catch (err: any) {
      setError('Failed to download ' + filename);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setError(null);
    }
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a .zip backup archive to import.');
      return;
    }

    setImporting(true);
    setError(null);
    setFeedback(null);

    try {
      await importSynonymBackup(
        selectedFile,
        expectedRevisionId.trim() || undefined
      );
      setFeedback('Synonym backup archive successfully imported and activated.');
      setSelectedFile(null);
      setExpectedRevisionId('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      if (onBackupImported) {
        onBackupImported();
      }
    } catch (err: any) {
      if (err instanceof ApiClientError) {
        if (err.status === 409 || err.code === 'revision_conflict') {
          setError('Revision conflict: Active synonym bundle changed. Please refresh and verify bundle revision.');
        } else if (err.status === 422) {
          setError('Invalid backup archive: ' + err.message);
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to import backup archive.');
      }
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className='synonym-backup-manager' style={{ display: 'grid', gap: 24 }}>
      {feedback && (
        <div
          role='status'
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            color: 'var(--success, #16a34a)',
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {feedback}
        </div>
      )}

      {error && (
        <div
          role='alert'
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            color: 'var(--danger, #dc2626)',
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      <div className='table-card' style={{ padding: 24, display: 'grid', gap: 16 }}>
        <div>
          <h3 style={{ margin: '0 0 4px', fontSize: 16 }}>Export Taxonomy & Synonym Archives</h3>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
            Download complete backup archives containing skills, domain, and role-family taxonomies or individual YAML policies.
          </p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <Button
            variant='primary'
            onClick={handleExportZip}
            loading={exporting}
            disabled={exporting}
          >
            Export Complete Backup (.zip)
          </Button>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Button
              variant='secondary'
              size='compact'
              onClick={() => handleDownloadYaml('/admin/synonyms/global.yaml', 'fitcv-global-skill-synonyms.yaml')}
            >
              Skills YAML
            </Button>
            <Button
              variant='secondary'
              size='compact'
              onClick={() => handleDownloadYaml('/admin/synonyms/global-domain.yaml', 'fitcv-global-domain-synonyms.yaml')}
            >
              Domain YAML
            </Button>
            <Button
              variant='secondary'
              size='compact'
              onClick={() => handleDownloadYaml('/admin/synonyms/global-role-family.yaml', 'fitcv-global-role-family-synonyms.yaml')}
            >
              Role Family YAML
            </Button>
          </div>
        </div>
      </div>

      <div className='table-card' style={{ padding: 24, display: 'grid', gap: 16 }}>
        <div>
          <h3 style={{ margin: '0 0 4px', fontSize: 16 }}>Import & Restore Synonym Backup</h3>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
            Restore synonym policies from a previously exported archive. Importing parses, normalizes, and activates the entire bundle.
          </p>
        </div>

        <form onSubmit={handleImport} style={{ display: 'grid', gap: 16, maxWidth: 520 }}>
          <div className='field-group'>
            <label htmlFor='synonym-backup-file' className='field-label'>
              Backup Archive File (.zip) <span className='required-mark' aria-hidden='true'>*</span>
            </label>
            <input
              ref={fileInputRef}
              id='synonym-backup-file'
              type='file'
              accept='.zip,application/zip'
              onChange={handleFileChange}
              disabled={importing}
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 10px',
                fontSize: 13,
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
              }}
            />
            <div className='field-hint' style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              Archive containing skill_synonyms.yaml, domain_synonyms.yaml, or role_family_synonyms.yaml.
            </div>
          </div>

          <div className='field-group'>
            <label htmlFor='synonym-expected-bundle-rev' className='field-label'>
              Expected Active Bundle Revision ID (Optional CAS guard)
            </label>
            <input
              id='synonym-expected-bundle-rev'
              type='text'
              className='field-input'
              value={expectedRevisionId}
              onChange={(e) => setExpectedRevisionId(e.target.value)}
              placeholder='e.g. bundle-revision-id'
              disabled={importing}
            />
          </div>

          <div>
            <Button
              type='submit'
              variant='primary'
              loading={importing}
              disabled={importing || !selectedFile}
            >
              Import & Activate Bundle
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
