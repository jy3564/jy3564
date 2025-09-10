'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface Report {
  id: number;
  title: string;
  created_at: string;
  authorEmail: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const fetchReports = async () => {
      const token = localStorage.getItem('authToken');
      if (!token) {
        router.replace('/login');
        return;
      }

      try {
        const res = await fetch('/api/reports', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.status === 401) {
          router.replace('/login');
          return;
        }

        if (!res.ok) {
          throw new Error('Failed to fetch reports');
        }

        const data = await res.json();
        setReports(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchReports();
  }, [router]);

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen">Loading reports...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center min-h-screen text-red-500">Error: {error}</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Research Reports</h1>
      <div className="space-y-4">
        {reports.length > 0 ? (
          reports.map((report) => (
            <Link href={`/reports/${report.id}`} key={report.id} className="block p-4 bg-white rounded-lg shadow hover:bg-gray-50">
              <h2 className="text-xl font-semibold text-indigo-600">{report.title}</h2>
              <p className="text-sm text-gray-500 mt-1">
                By {report.authorEmail} on {new Date(report.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))
        ) : (
          <p>No reports have been published yet.</p>
        )}
      </div>
    </div>
  );
}
