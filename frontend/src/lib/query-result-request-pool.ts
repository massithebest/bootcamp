/** 같은 키의 진행 중 요청만 공유한다. 완료 응답은 보관하지 않는다. */
interface InFlight<T> {
  controller: AbortController;
  promise: Promise<T>;
  subscribers: number;
  abortTimer: ReturnType<typeof setTimeout> | null;
}

export class RequestPool<T> {
  private readonly inFlight = new Map<string, InFlight<T>>();

  clear(): void {
    for (const request of this.inFlight.values()) request.controller.abort();
    this.inFlight.clear();
  }

  acquire(key: string, run: (signal: AbortSignal) => Promise<T>): {
    promise: Promise<T>;
    release: () => void;
  } {
    let request = this.inFlight.get(key);
    if (request?.controller.signal.aborted) {
      this.inFlight.delete(key);
      request = undefined;
    }
    if (!request) {
      const controller = new AbortController();
      const next: InFlight<T> = {
        controller,
        subscribers: 0,
        abortTimer: null,
        promise: Promise.resolve(null as never),
      };
      next.promise = run(controller.signal).then(
        (value) => {
          if (this.inFlight.get(key) === next) this.inFlight.delete(key);
          return value;
        },
        (error: unknown) => {
          if (this.inFlight.get(key) === next) this.inFlight.delete(key);
          throw error;
        },
      );
      this.inFlight.set(key, next);
      request = next;
    }
    if (request.abortTimer !== null) {
      clearTimeout(request.abortTimer);
      request.abortTimer = null;
    }
    request.subscribers += 1;
    const current = request;
    let released = false;
    return {
      promise: current.promise,
      release: () => {
        if (released) return;
        released = true;
        current.subscribers -= 1;
        if (current.subscribers === 0 && this.inFlight.get(key) === current) {
          current.abortTimer = setTimeout(() => {
            current.abortTimer = null;
            if (current.subscribers === 0 && this.inFlight.get(key) === current) {
              current.controller.abort();
              this.inFlight.delete(key);
            }
          }, 0);
        }
      },
    };
  }
}
