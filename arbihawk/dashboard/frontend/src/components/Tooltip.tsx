import { useState, useRef } from 'react';
import type { TooltipProps } from '../types';

interface TooltipStyle {
  placement: 'top' | 'bottom';
  xAlign: 'left' | 'right' | 'center';
}

/**
 * Tooltip component - only shows when text is provided
 */
export function Tooltip({ text, children, className = '' }: TooltipProps) {
  const [show, setShow] = useState(false);
  const [tooltipStyle, setTooltipStyle] = useState<TooltipStyle>({
    placement: 'top',
    xAlign: 'center',
  });
  const tooltipRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Don't add tooltip behavior if there's no text
  if (!text) {
    return <div className={className}>{children}</div>;
  }

  const updatePosition = () => {
    if (!tooltipRef.current || !containerRef.current) return;

    const tooltip = tooltipRef.current;
    const container = containerRef.current;
    const tooltipRect = tooltip.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    const viewportWidth = window.innerWidth;
    const margin = 8;

    const style: TooltipStyle = { placement: 'top', xAlign: 'center' };

    // Check if tooltip would overflow top - place below instead
    if (tooltipRect.top < margin) {
      style.placement = 'bottom';
    }

    // Check horizontal overflow
    const centerX = containerRect.left + containerRect.width / 2;
    const tooltipHalfWidth = tooltipRect.width / 2;

    if (centerX - tooltipHalfWidth < margin) {
      style.xAlign = 'left';
    } else if (centerX + tooltipHalfWidth > viewportWidth - margin) {
      style.xAlign = 'right';
    }

    setTooltipStyle(style);
  };

  const handleMouseEnter = () => {
    setShow(true);
    // Use requestAnimationFrame to ensure DOM is updated
    requestAnimationFrame(() => {
      requestAnimationFrame(updatePosition);
    });
  };

  const isFullWidth = className.includes('w-full');
  const containerClass = isFullWidth 
    ? `relative flex items-center ${className}`
    : `relative inline-flex items-center ${className}`;
  
  return (
    <div
      ref={containerRef}
      className={containerClass}
    >
      <div
        onMouseEnter={handleMouseEnter}
        onMouseLeave={() => setShow(false)}
        className={isFullWidth ? 'cursor-help w-full' : 'cursor-help'}
      >
        {children}
      </div>
      {show && (
        <div
          ref={tooltipRef}
          className={`absolute z-50 min-w-[200px] max-w-xs whitespace-normal rounded border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 shadow-lg ${
            tooltipStyle.placement === 'bottom'
              ? 'top-full mt-2'
              : 'bottom-full mb-2'
          } ${
            tooltipStyle.xAlign === 'left'
              ? 'left-0'
              : tooltipStyle.xAlign === 'right'
                ? 'right-0'
                : 'left-1/2 -translate-x-1/2'
          }`}
        >
          {text}
          <div
            className={`absolute ${
              tooltipStyle.placement === 'bottom'
                ? 'bottom-full left-1/2 -translate-x-1/2 border-4 border-transparent border-b-slate-900'
                : 'left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-slate-900'
            }`}
          />
        </div>
      )}
    </div>
  );
}
