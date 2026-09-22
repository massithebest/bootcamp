/** 콜백으로 들어오는 값을 async iteration으로 바꾸는 작은 큐. 도착한 값은 배치로 넘긴다. */
export class EventQueue<T> {
  private items: T[] = [];
  private waiter: (() => void) | null = null;
  private closed = false;

  push(item: T): void {
    if (this.closed) return;
    this.items.push(item);
    this.wake();
  }

  close(): void {
    this.closed = true;
    this.wake();
  }

  private wake(): void {
    const waiter = this.waiter;
    this.waiter = null;
    waiter?.();
  }

  /** 닫힌 뒤 남은 값까지 모두 넘기고 끝난다. */
  async *batches(): AsyncGenerator<T[], void, void> {
    for (;;) {
      if (this.items.length > 0) {
        const batch = this.items;
        this.items = [];
        yield batch;
        continue;
      }
      if (this.closed) return;
      await new Promise<void>((resolve) => {
        this.waiter = resolve;
      });
    }
  }
}
