'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  role: string;
}

export default function HomePage() {
  const router = useRouter();
  const [userRole, setUserRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      router.replace('/login');
      return;
    }

    try {
      const decoded: DecodedToken = jwtDecode(token);
      setUserRole(decoded.role);
    } catch (error) {
      // Invalid token
      router.replace('/login');
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-50 text-gray-800">
      <div className="w-full max-w-4xl text-center">
        <h1 className="text-4xl font-bold mb-4">Welcome to the Dashboard</h1>
        <p className="text-lg text-gray-600 mb-10">Your central hub for research and real-time signals.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Reports Card */}
          <Link href="/reports" className="block p-8 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
            <h2 className="text-2xl font-semibold mb-2 text-indigo-600">Research Reports</h2>
            <p className="text-gray-500">Access in-depth analysis and institutional-grade research papers.</p>
          </Link>

          {/* Signals Card */}
          <Link href="/signals" className="block p-8 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
            <h2 className="text-2xl font-semibold mb-2 text-teal-600">Trading Signals</h2>
            <p className="text-gray-500">View real-time trading alerts and market notifications.</p>
          </Link>

          {/* Admin Dashboard Link - Conditional */}
          {userRole === 'admin' && (
            <Link href="/admin" className="md:col-span-2 block p-8 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow border-t-4 border-purple-500 mt-4">
              <h2 className="text-2xl font-semibold mb-2 text-purple-600">Admin Panel</h2>
              <p className="text-gray-500">Manage users, publish new reports, and configure site settings.</p>
            </Link>
          )}
        </div>
      </div>
    </main>
  );
}
