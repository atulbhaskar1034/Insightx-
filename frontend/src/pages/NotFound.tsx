import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="text-center">
        <h1 className="mb-4 text-6xl font-black landing-stat-gradient-orange">404</h1>
        <p className="mb-6 text-xl text-gray-500">Oops! Page not found</p>
        <Link
          to="/"
          className="landing-btn-primary text-sm"
        >
          Return to Home
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
