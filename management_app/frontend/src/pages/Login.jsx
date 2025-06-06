import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';

export default function Login({ onLogin }) {
  const [user, setUser] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    setError('');
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user)
    });
    const data = await res.json();
    if (res.ok && data.token) {
      localStorage.setItem('token', data.token);
      if (onLogin) onLogin(data.token);
      navigate('/dashboard');
    } else {
      setError(data.error || 'Incorrect username or password');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleLogin();
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2 className="login-title">Business Portal Login</h2>
        <input
          className="login-input"
          placeholder="Username"
          onChange={e => setUser({ ...user, username: e.target.value })}
          onKeyDown={handleKeyDown}
        />
        <input
          className="login-input"
          placeholder="Password"
          type="password"
          onChange={e => setUser({ ...user, password: e.target.value })}
          onKeyDown={handleKeyDown}
        />
        <button className="login-button" onClick={handleLogin}>Login</button>
        {error && <div className="login-error">{error}</div>}
      </div>
    </div>
  );
}
