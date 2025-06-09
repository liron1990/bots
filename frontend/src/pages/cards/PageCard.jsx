import React from 'react';

export default function PageCard({ title, edit, onEdit, onSave, onCancel, children }) {
  return (
    <div className="page-container">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem'
      }}>
        <h2 style={{ margin: 0 }}>{title}</h2>
        {edit !== undefined && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {edit ? (
              <>
                <button className="common-btn" onClick={onSave}>Save</button>
                <button className="common-btn" onClick={onCancel}>Back</button>
              </>
            ) : (
              <button className="common-btn" onClick={onEdit}>Edit</button>
            )}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}