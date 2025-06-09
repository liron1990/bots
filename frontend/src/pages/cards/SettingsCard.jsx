import { useEffect, useState, useRef } from 'react';
import PageCard from './PageCard';

export default function SettingsCard() {
  const [settings, setSettings] = useState(null);
  const [msg, setMsg] = useState('');
  const [edit, setEdit] = useState(false);
  const originalSettings = useRef(null);

  useEffect(() => {
    fetch('/api/settings', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => {
        setSettings(data);
        originalSettings.current = data;
      });
  }, []);

  const handleEdit = () => {
    originalSettings.current = structuredClone(settings);
    setEdit(true);
  };

  const handleCancel = () => {
    setSettings(structuredClone(originalSettings.current));
    setEdit(false);
    setMsg('');
  };

  const handleChange = (e) => {
    setSettings({ ...settings, [e.target.name]: e.target.value });
  };

  const handleSave = async () => {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(settings)
    });
    const data = await res.json();
    setMsg(data.success ? 'Saved!' : data.error);
    setEdit(false);
  };

  if (!settings) return <div style={{ padding: "2rem" }}><h2>Settings</h2>Loading...</div>;

  return (
    <PageCard
      title="Settings"
      edit={edit}
      onEdit={handleEdit}
      onSave={handleSave}
      onCancel={handleCancel}
    >
      {Object.entries(settings).map(([k, v]) =>
        edit ? (
          <div key={k}>
            <label>{k}: </label>
            <input
              name={k}
              value={v}
              onChange={handleChange}
              style={{ color: '#222', background: '#f8fafc' }}
            />
          </div>
        ) : (
          <div key={k} style={{ color: '#222' }}>
            <b>{k}:</b> {v}
          </div>
        )
      )}
      <div>{msg}</div>
    </PageCard>
  );
}