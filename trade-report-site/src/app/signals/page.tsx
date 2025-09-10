'use client';

import useSWR from 'swr';
import { useRouter } from 'next/navigation';

interface Signal {
  id: number;
  raw_content: string;
  received_at: string;
}

const fetcher = async (url: string) => {
  const token = localStorage.getItem('authToken');
  if (!token) {
    // This case will be handled by the error boundary of SWR
    throw new Error('Not authorized');
  }

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (res.status === 401) {
    throw new Error('Not authorized');
  }

  if (!res.ok) {
    throw new Error('Failed to fetch signals');
  }

  return res.json();
};

export default function SignalsPage() {
  const router = useRouter();
  const { data: signals, error, isLoading } = useSWR<Signal[]>('/api/signals', fetcher, {
    refreshInterval: 5000, // Refresh every 5 seconds
    onError: () => {
      // If fetcher throws, SWR's onError is triggered.
      router.replace('/login');
    },
  });

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading signals...</div>;
  }

  if (error) {
    // The onError handler above should have already redirected.
    // This is a fallback.
    return <div className="flex justify-center items-center min-h-screen text-red-500">Could not load signals. Please log in.</div>;
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Real-time Trading Signals</h1>
      <div className="space-y-4">
        {signals && signals.length > 0 ? (
          signals.map((signal) => (
            <div key={signal.id} className="p-4 bg-white rounded-lg shadow">
              <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800">{signal.raw_content}</pre>
              <p className="text-xs text-gray-400 mt-2 text-right">
                Received: {new Date(signal.received_at).toLocaleString()}
              </p>
            </div>
          ))
        ) : (
          <p>No signals received yet. Waiting for new data...</p>
        )}
      </div>
    </div>
  );
}
