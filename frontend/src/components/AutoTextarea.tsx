import React, { useRef, useEffect } from "react";

interface AutoTextareaProps {
  value: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  readOnly?: boolean;
  placeholder?: string;
  className?: string;
  minRows?: number;
}

export default function AutoTextarea({
  value,
  onChange,
  readOnly,
  placeholder,
  className = "",
  minRows = 1,
}: AutoTextareaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    }
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={onChange}
      readOnly={readOnly}
      placeholder={placeholder}
      rows={minRows}
      className={className}
    />
  );
}