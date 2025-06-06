import { useEffect, useState } from 'react';
import axios from 'axios';

export default function Protected() {
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    axios.get('/api/protected', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => setMsg(res.data.data))
    .catch(() => setMsg("Access denied"));
  }, []);

  const handleLogout = async () => {
    await axios.post('/api/logout');
    localStorage.removeItem('token');
    window.location.reload();
  };

  return (
    <div>
      <h2>{msg}</h2>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}
