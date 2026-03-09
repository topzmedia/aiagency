'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value?: number[];
  onValueChange?: (value: number[]) => void;
  min?: number;
  max?: number;
  step?: number;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value = [0], onValueChange, min = 0, max = 100, step = 1, ...props }, ref) => {
    return (
      <div className={cn('relative flex w-full touch-none select-none items-center', className)}>
        <input
          ref={ref}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value[0]}
          onChange={(e) => onValueChange?.([Number(e.target.value)])}
          className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
          {...props}
        />
      </div>
    );
  }
);
Slider.displayName = 'Slider';

export { Slider };
