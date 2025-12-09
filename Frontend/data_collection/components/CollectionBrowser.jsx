import { useState, useEffect } from 'react';
import { listCollections, getCollectionDocuments, exportCollectionCSV } from '../api';

export default function CollectionBrowser() {
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [total, setTotal] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');

  useEffect(() => {
    loadCollections();
  }, []);

  useEffect(() => {
    if (selectedCollection) {
      loadDocuments();
    }
  }, [selectedCollection, page, limit, searchQuery]);

  async function loadCollections() {
    try {
      setError(null);
      const data = await listCollections();
      setCollections(data);
    } catch (err) {
      const errorMsg = err.message || 'Failed to connect to backend. Make sure the backend server is running.';
      setError(errorMsg);
      console.error('Failed to load collections:', err);
    }
  }

  async function loadDocuments() {
    if (!selectedCollection) return;
    setLoading(true);
    try {
      setError(null);
      const data = await getCollectionDocuments(selectedCollection, page, limit, searchQuery || null);
      setDocuments(data.docs || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleCollectionSelect(collectionName) {
    setSelectedCollection(collectionName);
    setPage(1);
    setSearchQuery('');
    setSearchInput('');
  }

  function handleSearch() {
    setSearchQuery(searchInput);
    setPage(1);
  }

  function handleExport() {
    if (!selectedCollection) return;
    exportCollectionCSV(selectedCollection, searchQuery || null).catch((err) => {
      setError(err.message);
      console.error('Failed to export CSV:', err);
    });
  }

  function getTableHeaders() {
    if (documents.length === 0) return [];
    const headers = new Set();
    documents.forEach((doc) => {
      Object.keys(doc).forEach((key) => headers.add(key));
    });
    return Array.from(headers).sort();
  }

  const totalPages = Math.ceil(total / limit);
  const headers = getTableHeaders();

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '20px' }}>Collection Browser</h1>

      {error && (
        <div style={{ padding: '12px', marginBottom: '16px', background: '#f8d7da', color: '#721c24', borderRadius: '4px' }}>
          Error: {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 120px)' }}>
        {/* Collections Sidebar */}
        <div style={{ width: '250px', border: '1px solid #e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ padding: '12px', background: '#fafafa', borderBottom: '1px solid #e0e0e0', fontWeight: '600' }}>
            Collections ({collections.length})
          </div>
          <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 180px)' }}>
            {collections.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>No collections found</div>
            ) : (
              collections.map((name) => (
                <div
                  key={name}
                  onClick={() => handleCollectionSelect(name)}
                  style={{
                    padding: '12px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f0f0f0',
                    background: selectedCollection === name ? '#e7f3ff' : 'white',
                    borderLeft: selectedCollection === name ? '3px solid #007bff' : '3px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedCollection !== name) e.currentTarget.style.background = '#f8f9fa';
                  }}
                  onMouseLeave={(e) => {
                    if (selectedCollection !== name) e.currentTarget.style.background = 'white';
                  }}
                >
                  {name}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Documents Table */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid #e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
          {selectedCollection ? (
            <>
              {/* Header with search and export */}
              <div style={{ padding: '16px', background: '#fafafa', borderBottom: '1px solid #e0e0e0', display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px' }}>{selectedCollection}</div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="text"
                      placeholder="Search (name or url)..."
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      style={{ flex: 1, padding: '6px 12px', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                    <button
                      onClick={handleSearch}
                      style={{ padding: '6px 16px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      Search
                    </button>
                    <button
                      onClick={handleExport}
                      style={{ padding: '6px 16px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      Export CSV
                    </button>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div style={{ flex: 1, overflow: 'auto' }}>
                {loading ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>Loading...</div>
                ) : documents.length === 0 ? (
                  <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>No documents found</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead style={{ background: '#f8f9fa', position: 'sticky', top: 0 }}>
                      <tr>
                        {headers.map((header) => (
                          <th
                            key={header}
                            style={{
                              padding: '12px',
                              textAlign: 'left',
                              borderBottom: '2px solid #dee2e6',
                              fontWeight: '600',
                              fontSize: '13px',
                            }}
                          >
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                          {headers.map((header) => (
                            <td
                              key={header}
                              style={{
                                padding: '12px',
                                fontSize: '13px',
                                maxWidth: '300px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                              title={String(doc[header] || '')}
                            >
                              {typeof doc[header] === 'object' ? JSON.stringify(doc[header]) : String(doc[header] || '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Pagination */}
              <div style={{ padding: '12px', background: '#fafafa', borderTop: '1px solid #e0e0e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '13px', color: '#666' }}>
                  Showing {(page - 1) * limit + 1} to {Math.min(page * limit, total)} of {total} documents
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <label style={{ fontSize: '13px', marginRight: '8px' }}>
                    Per page:
                    <select
                      value={limit}
                      onChange={(e) => {
                        setLimit(Number(e.target.value));
                        setPage(1);
                      }}
                      style={{ marginLeft: '8px', padding: '4px', border: '1px solid #ddd', borderRadius: '4px' }}
                    >
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={200}>200</option>
                    </select>
                  </label>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={{
                      padding: '6px 12px',
                      background: page === 1 ? '#e9ecef' : '#007bff',
                      color: page === 1 ? '#999' : 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page === 1 ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Previous
                  </button>
                  <span style={{ padding: '0 12px', fontSize: '13px' }}>
                    Page {page} of {totalPages || 1}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    style={{
                      padding: '6px 12px',
                      background: page >= totalPages ? '#e9ecef' : '#007bff',
                      color: page >= totalPages ? '#999' : 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>Select a collection to view documents</div>
          )}
        </div>
      </div>
    </div>
  );
}

