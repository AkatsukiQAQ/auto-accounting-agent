import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    // eslint-disable-next-line no-console
    console.error('Render error:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full items-center justify-center p-6">
          <div className="max-w-md space-y-3 text-center">
            <h1 className="text-lg font-semibold text-ink-900">Something went wrong</h1>
            <p className="text-sm text-ink-700">
              An unexpected error broke the page. Try reloading; if it keeps happening, check the
              browser console.
            </p>
            <pre className="overflow-auto rounded-lg bg-cream-100 p-3 text-left text-xs text-neg-500">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-lg bg-ink-900 px-4 py-2 text-sm text-cream-50 hover:bg-ink-700"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
