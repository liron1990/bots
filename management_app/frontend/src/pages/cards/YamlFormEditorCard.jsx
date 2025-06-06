import { useEffect, useState, useRef } from 'react';
import PageCard from './PageCard';
import '../YamlFormEditor.css';

export default function YamlFormEditorCard() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState('');
  const [collapsed, setCollapsed] = useState({});
  const [collapsedInitialized, setCollapsedInitialized] = useState(false);
  const [edit, setEdit] = useState(false);
  const originalData = useRef(null);

  // Helper to set all keys collapsed by default (only root open)
  const setAllCollapsed = (obj, path = [], acc = {}) => {
    if (typeof obj === 'object' && obj !== null) {
      const key = path.join('.');
      acc[key] = path.length > 0;
      if (Array.isArray(obj)) {
        obj.forEach((item, i) => setAllCollapsed(item, [...path, i], acc));
      } else {
        Object.entries(obj).forEach(([k, v]) => setAllCollapsed(v, [...path, k], acc));
      }
    }
    return acc;
  };

  // Fetch YAML data with JWT
  useEffect(() => {
    const token = localStorage.getItem('token');
    fetch(`/api/yaml`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        setData(data);
        originalData.current = data;
      });
  }, []);

  // Only set collapsed state when data is first loaded
  useEffect(() => {
    if (data && !collapsedInitialized) {
      setCollapsed(setAllCollapsed(data));
      setCollapsedInitialized(true);
    }
    // eslint-disable-next-line
  }, [data, collapsedInitialized]);

  const handleChange = (path, value) => {
    const newData = structuredClone(data);
    let ptr = newData;
    for (let i = 0; i < path.length - 1; i++) {
      ptr = ptr[path[i]];
    }
    ptr[path[path.length - 1]] = value;
    setData(newData);
  };

  const toggleCollapse = (path) => {
    const key = path.join('.');
    setCollapsed(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const renderFields = (obj, path = []) => {
    if (typeof obj === 'object' && obj !== null) {
      const key = path.join('.');
      const isCollapsed = collapsed[key];
      if (Array.isArray(obj)) {
        return (
          <div className="yaml-array">
            <span
              className="yaml-collapse"
              onClick={() => toggleCollapse(path)}
            >
              {isCollapsed ? '▶' : '▼'} [{obj.length}]
            </span>
            {!isCollapsed && obj.map((item, i) => (
              <div key={i} className="yaml-array-item">
                {renderFields(item, [...path, i])}
              </div>
            ))}
          </div>
        );
      } else {
        return (
          <div className="yaml-object">
            <span
              className="yaml-collapse"
              onClick={() => toggleCollapse(path)}
            >
              {isCollapsed ? '▶' : '▼'}
            </span>
            {!isCollapsed && Object.entries(obj).map(([key, value]) => (
              <div key={key} className="yaml-field">
                <label className="yaml-label">{key}</label>
                {renderFields(value, [...path, key])}
              </div>
            ))}
          </div>
        );
      }
    } else {
      const sharedStyle = {
        width: '100%',
        background: '#f8fafc',
        borderRadius: '8px',
        fontSize: '1.1rem',
        padding: '0.75rem',
        boxSizing: 'border-box',
        color: '#222', // <-- Add this line for dark text
        // Remove maxHeight here for textarea
      };
      return edit ? (
        <textarea
          className="yaml-input"
          style={{
            ...sharedStyle,
            border: '1.5px solid #d1d9e6',
            resize: 'vertical',
            minHeight: 40
          }}
          value={obj}
          onChange={(e) => handleChange(path, e.target.value)}
          rows={Math.max(2, String(obj).split('\n').length)}
        />
      ) : (
        <div
          className="yaml-view"
          style={{
            ...sharedStyle,
            border: 'none',
            whiteSpace: 'pre-wrap',
            minHeight: 40,
            maxHeight: 300,
            overflowY: 'auto'
          }}
        >
          {obj}
        </div>
      );
    }
  };

  const handleSave = async () => {
    const token = localStorage.getItem('token');
    const res = await fetch(`/api/yaml`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    setMsg(result.success ? 'Saved!' : result.error);
    setEdit(false);
  };

  const handleEdit = () => {
    originalData.current = structuredClone(data);
    setEdit(true);
  };

  const handleCancel = () => {
    setData(structuredClone(originalData.current));
    setEdit(false);
    setMsg('');
  };

  if (!data) return <div className="yaml-loading">Loading...</div>;

  return (
    <PageCard
      title="Edit YAML Settings"
      edit={edit}
      onEdit={handleEdit}
      onSave={handleSave}
      onCancel={handleCancel}
    >
      <div className="yaml-editor-scroll">
        {renderFields(data)}
      </div>
      <p className="yaml-msg">{msg}</p>
    </PageCard>
  );
}