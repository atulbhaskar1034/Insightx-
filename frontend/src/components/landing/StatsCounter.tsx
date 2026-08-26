import { motion } from "framer-motion";
import { useEffect, useState, useRef } from "react";

interface Stat {
  value: string;
  suffix: string;
  label: string;
  gradient: string;
}

const stats: Stat[] = [
  {
    value: "250K",
    suffix: "+",
    label: "TRANSACTIONS ANALYZED",
    gradient: "landing-stat-gradient-orange",
  },
  {
    value: "5",
    suffix: "",
    label: "AI MODELS INTEGRATED",
    gradient: "landing-stat-gradient-pink",
  },
  {
    value: "30",
    suffix: "-Day",
    label: "FORECASTING HORIZON",
    gradient: "landing-stat-gradient-cyan",
  },
  {
    value: "<2",
    suffix: "s",
    label: "AVERAGE QUERY RESPONSE",
    gradient: "landing-stat-gradient-violet",
  },
];

const StatsCounter = () => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="max-w-5xl mx-auto">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={isVisible ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="text-center"
          >
            <p className={`text-5xl md:text-6xl font-black ${stat.gradient}`}>
              {stat.value}
              <span className="text-3xl md:text-4xl">{stat.suffix}</span>
            </p>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-[0.15em] mt-3">
              ■ {stat.label} ■
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default StatsCounter;
