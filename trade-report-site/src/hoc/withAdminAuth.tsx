'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  role: string;
  exp: number;
}

const withAdminAuth = <P extends object>(WrappedComponent: React.ComponentType<P>) => {
  const WithAdminAuthComponent = (props: P) => {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
      const token = localStorage.getItem('authToken');
      if (!token) {
        router.replace('/login');
        return;
      }

      try {
        const decodedToken: DecodedToken = jwtDecode(token);
        const isTokenExpired = Date.now() >= decodedToken.exp * 1000;

        if (decodedToken.role !== 'admin' || isTokenExpired) {
          localStorage.removeItem('authToken'); // Clean up invalid token
          router.replace('/login');
        } else {
          setIsLoading(false);
        }
      } catch (error) {
        localStorage.removeItem('authToken'); // Clean up corrupted token
        router.replace('/login');
      }
    }, [router]);

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <p>Loading and verifying credentials...</p>
        </div>
      );
    }

    return <WrappedComponent {...props} />;
  };

  return WithAdminAuthComponent;
};

export default withAdminAuth;
