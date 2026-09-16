import { cn } from "@/lib/utils";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-control bg-surface-subtle",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
