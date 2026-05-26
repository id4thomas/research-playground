import { useCallback, useEffect, useRef } from "react";

type Props = { onDrag: (dx: number) => void };

export function Resizer({ onDrag }: Props) {
  const dragging = useRef(false);
  const last = useRef(0);

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!dragging.current) return;
      onDrag(e.clientX - last.current);
      last.current = e.clientX;
    },
    [onDrag]
  );
  const stop = useCallback(() => { dragging.current = false; }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", stop);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", stop);
    };
  }, [onMouseMove, stop]);

  return (
    <div
      className="w-1 shrink-0 cursor-col-resize bg-slate-200 hover:bg-slate-400 transition-colors"
      onMouseDown={(e) => {
        dragging.current = true;
        last.current = e.clientX;
        e.preventDefault();
      }}
    />
  );
}
