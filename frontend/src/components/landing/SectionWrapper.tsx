import { motion } from "framer-motion";
import { ReactNode } from "react";

interface SectionWrapperProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  label?: string;
  className?: string;
  id?: string;
}

const SectionWrapper = ({
  children,
  title,
  subtitle,
  label,
  className = "",
  id,
}: SectionWrapperProps) => {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5 }}
      className={`relative px-6 py-20 md:py-28 ${className}`}
    >
      {(label || title || subtitle) && (
        <div className="text-center mb-14">
          {label && (
            <p className="landing-section-label justify-center">{label}</p>
          )}
          {title && (
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="text-base md:text-lg text-gray-500 max-w-xl mx-auto">
              {subtitle}
            </p>
          )}
        </div>
      )}
      {children}
    </motion.section>
  );
};

export default SectionWrapper;
