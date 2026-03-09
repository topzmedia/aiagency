'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface SheetContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SheetContext = React.createContext<SheetContextValue>({
  open: false,
  setOpen: () => {},
});

function Sheet({
  children,
  open: controlledOpen,
  onOpenChange,
}: {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(false);
  const open = controlledOpen ?? uncontrolledOpen;
  const setOpen = onOpenChange ?? setUncontrolledOpen;

  return (
    <SheetContext.Provider value={{ open, setOpen }}>
      {children}
    </SheetContext.Provider>
  );
}

function SheetTrigger({
  children,
  asChild,
}: {
  children: React.ReactNode;
  asChild?: boolean;
}) {
  const { setOpen } = React.useContext(SheetContext);

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<{ onClick?: () => void }>, {
      onClick: () => setOpen(true),
    });
  }

  return (
    <button type="button" onClick={() => setOpen(true)}>
      {children}
    </button>
  );
}

function SheetContent({
  children,
  className,
  side = 'right',
}: {
  children: React.ReactNode;
  className?: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
}) {
  const { open, setOpen } = React.useContext(SheetContext);

  if (!open) return null;

  const sideClasses = {
    top: 'inset-x-0 top-0 border-b',
    bottom: 'inset-x-0 bottom-0 border-t',
    left: 'inset-y-0 left-0 h-full w-3/4 border-r sm:max-w-sm',
    right: 'inset-y-0 right-0 h-full w-3/4 border-l sm:max-w-sm',
  };

  return (
    <div className="fixed inset-0 z-50">
      <div className="fixed inset-0 bg-black/80" onClick={() => setOpen(false)} />
      <div
        className={cn(
          'fixed z-50 gap-4 bg-background p-6 shadow-lg transition ease-in-out',
          sideClasses[side],
          className
        )}
      >
        {children}
        <button
          className="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100"
          onClick={() => setOpen(false)}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function SheetHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex flex-col space-y-2 text-center sm:text-left', className)} {...props} />
  );
}

function SheetTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-lg font-semibold text-foreground', className)} {...props} />;
}

function SheetDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />;
}

export { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetDescription };
