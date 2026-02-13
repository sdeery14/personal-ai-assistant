"use client";

import { Component, ReactNode } from "react";
import { Button, Card } from "@/components/ui";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center p-4">
          <Card padding="lg" className="max-w-md text-center">
            <h2 className="text-lg font-semibold text-gray-900">
              Something went wrong
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            {this.state.error && (
              <p className="mt-2 rounded bg-gray-50 p-2 text-xs text-gray-500">
                {this.state.error.message}
              </p>
            )}
            <Button
              className="mt-4"
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
            >
              Refresh page
            </Button>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
