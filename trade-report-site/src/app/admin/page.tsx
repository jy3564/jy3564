'use client';

import React, { useState } from 'react';
import { TiptapEditor } from '@/components/TiptapEditor';
import withAdminAuth from '@/hoc/withAdminAuth';

function AdminDashboardPage() {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    const token = localStorage.getItem('authToken');
    if (!token) {
      setError('You are not authorized. Please log in.');
      return;
    }

    try {
      const res = await fetch('/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, content }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Failed to create report');
      }

      setMessage('Report created successfully!');
      setTitle('');
      setContent(''); // Clear editor content after submission
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl p-4 mx-auto sm:p-6 lg:p-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Admin Dashboard</h1>
        <p className="mt-2 text-lg text-gray-600">Create a new research report.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700">
              Report Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="block w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Report Content
            </label>
            <div className="mt-1">
              <TiptapEditor content={content} onChange={setContent} />
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {message && <p className="text-sm text-green-600">{message}</p>}

          <div>
            <button
              type="submit"
              className="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Publish Report
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default withAdminAuth(AdminDashboardPage);
