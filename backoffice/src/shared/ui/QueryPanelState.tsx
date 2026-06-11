import { EmptyState } from "@/shared/ui/EmptyState";

type QueryPanelStateProps = {
  isError: boolean;
  isLoading: boolean;
  loadingTitle: string;
  loadingDescription: string;
  errorTitle: string;
  errorDescription: string;
};

export function QueryPanelState({
  isError,
  isLoading,
  loadingTitle,
  loadingDescription,
  errorTitle,
  errorDescription
}: QueryPanelStateProps) {
  if (isLoading) {
    return <EmptyState title={loadingTitle} description={loadingDescription} />;
  }

  if (isError) {
    return <EmptyState title={errorTitle} description={errorDescription} />;
  }

  return null;
}
