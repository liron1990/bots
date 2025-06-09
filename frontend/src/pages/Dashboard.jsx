import { useState } from 'react';
import './cards/DashboardCards.css';
import YamlFormEditorCard from './cards/YamlFormEditorCard';
import SettingsCard from './cards/SettingsCard';
import PromptCard from './cards/PromptCard';

const TABS = [
  { key: 'yaml', label: 'YAML Editor', component: <YamlFormEditorCard /> },
  { key: 'settings', label: 'Settings', component: <SettingsCard /> },
  { key: 'prompt', label: 'Prompt Editor', component: <PromptCard /> },
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('yaml');

  return (
    <div
      style={{
        width: "100vw",
        minHeight: "100vh",
        background: "#f8fafc",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column"
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "2rem",
          borderBottom: "2px solid #e0e7ef",
          background: "#fff",
          padding: "0.5rem 0",
          position: "sticky",
          top: 0,
          zIndex: 10
        }}
      >
        {TABS.map(tab => (
          <button
            key={tab.key}
            className={`dashboard-tab${activeTab === tab.key ? ' active' : ''} common-btn`}
            onClick={() => setActiveTab(tab.key)}
            style={{
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.key ? "3px solid #4a90e2" : "3px solid transparent",
              color: activeTab === tab.key ? "#4a90e2" : "#2a3b4c",
              fontWeight: activeTab === tab.key ? 600 : 400,
              fontSize: "1.1rem",
              padding: "0.5rem 1.5rem",
              cursor: "pointer",
              outline: "none",
              transition: "border 0.2s, color 0.2s"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div
        style={{
          flex: 1,
          width: "100vw",
          minHeight: "calc(100vh - 60px)",
          margin: 0,
          padding: 0,
          background: "#fff",
          borderRadius: 0,
          boxShadow: "none",
          display: "flex",
          flexDirection: "column",
          overflow: "auto"
        }}
      >
        {TABS.find(tab => tab.key === activeTab)?.component}
      </div>
    </div>
  );
}