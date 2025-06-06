import { useEffect, useState, useRef } from 'react';
import PageCard from './PageCard';

const sharedStyle = {
  width: '100%',
  background: '#f8fafc',
  borderRadius: '8px',
  fontSize: '1.1rem',
  padding: '0.75rem',
  boxSizing: 'border-box',
  color: '#222' // <-- add this line
};

export default function PromptCard() {
  const [prompt, setPrompt] = useState('');
  const [msg, setMsg] = useState('');
  const [edit, setEdit] = useState(false);
  const originalPrompt = useRef('');

  useEffect(() => {
    fetch('/api/prompt', {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => {
        setPrompt(data.prompt || '');
        originalPrompt.current = data.prompt || '';
      });
  }, []);

  const handleEdit = () => {
    originalPrompt.current = prompt;
    setEdit(true);
  };

  const handleCancel = () => {
    setPrompt(originalPrompt.current);
    setEdit(false);
    setMsg('');
  };

  const handleSave = async () => {
    const res = await fetch('/api/prompt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ prompt })
    });
    const data = await res.json();
    setMsg(data.success ? 'Saved!' : data.error);
    setEdit(false);
  };

  return (
    <PageCard
      title="Prompt Editor"
      edit={edit}
      onEdit={handleEdit}
      onSave={handleSave}
      onCancel={handleCancel}
    >
      {edit ? (
        <textarea
          style={{
            ...sharedStyle,
            minHeight: 'calc(100vh - 220px)',
            maxHeight: 'calc(100vh - 220px)',
            resize: 'vertical',
            overflowY: 'auto',
            border: '1.5px solid #d1d9e6'
          }}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
        />
      ) : (
        <div
          style={{
            ...sharedStyle,
            minHeight: 'calc(100vh - 220px)',
            maxHeight: 'calc(100vh - 220px)',
            overflowY: 'auto'
          }}
        >
          {prompt}
        </div>
      )}
      <div>{msg}</div>
    </PageCard>
  );
}