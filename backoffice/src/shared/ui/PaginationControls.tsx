type PaginationControlsProps = {
  limit: number;
  offset: number;
  itemCount: number;
  onPrevious: () => void;
  onNext: () => void;
};

export function PaginationControls({
  limit,
  offset,
  itemCount,
  onPrevious,
  onNext
}: PaginationControlsProps) {
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="pagination">
      <span>Pagina {currentPage}</span>
      <div>
        <button className="button ghost" disabled={offset === 0} onClick={onPrevious} type="button">
          Anterior
        </button>
        <button className="button ghost" disabled={itemCount < limit} onClick={onNext} type="button">
          Siguiente
        </button>
      </div>
    </div>
  );
}
