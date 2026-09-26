import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { PlayerTrack, PlayerPlaylist } from '../../api/types';
import { PlayerSidebar, PlayerNavSection } from './PlayerSidebar';
import { PlayerHeader, ViewMode, SortOption } from './PlayerHeader';
import { TrackTableView } from './TrackTableView';
import { TrackGridView } from './TrackGridView';
import { MetadataEditModal } from './MetadataEditModal';
import { PlaylistModal } from './PlaylistModal';
import { PlayerRightSidebar } from './PlayerRightSidebar';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { Music, FolderSearch, Loader2 } from 'lucide-react';

export const PlayerWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { rightPanelTab } = useAudioPlayer();

  // Resizable Sidebars State & Persistence
  const [leftWidth, setLeftWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('auralytica_player_left_width');
      if (saved) {
        const val = Number(saved);
        if (!isNaN(val) && val >= 180 && val <= 420) return val;
      }
    } catch {}
    return 240;
  });

  const [rightWidth, setRightWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('auralytica_player_right_width');
      if (saved) {
        const val = Number(saved);
        if (!isNaN(val) && val >= 240 && val <= 500) return val;
      }
    } catch {}
    return 320;
  });

  const handleLeftResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = leftWidth;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientX - startX;
      const newWidth = Math.max(180, Math.min(420, startWidth + delta));
      setLeftWidth(newWidth);
    };

    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setLeftWidth((w) => {
        try {
          localStorage.setItem('auralytica_player_left_width', String(w));
        } catch {}
        return w;
      });
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const handleRightResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightWidth;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const delta = startX - moveEvent.clientX;
      const newWidth = Math.max(240, Math.min(500, startWidth + delta));
      setRightWidth(newWidth);
    };

    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setRightWidth((w) => {
        try {
          localStorage.setItem('auralytica_player_right_width', String(w));
        } catch {}
        return w;
      });
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  // Navigation State
  const [currentSection, setCurrentSection] = useState<PlayerNavSection>({ type: 'all' });
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [sortOption, setSortOption] = useState<SortOption>('title_asc');

  // Modals state
  const [editingTrack, setEditingTrack] = useState<PlayerTrack | null>(null);
  const [playlistModalMode, setPlaylistModalMode] = useState<'create' | 'edit' | 'import' | null>(
    null
  );
  const [editingPlaylist, setEditingPlaylist] = useState<PlayerPlaylist | null>(null);

  // Notification Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Queries
  const { data: libraryData, isLoading: isLoadingLibrary, refetch: refetchLibrary } = useQuery({
    queryKey: ['player-library'],
    queryFn: () => api.getPlayerLibrary(),
  });

  const { data: playlists = [], refetch: refetchPlaylists } = useQuery({
    queryKey: ['player-playlists'],
    queryFn: () => api.getPlayerPlaylists(),
  });

  // Query playlist tracks if in playlist view
  const activePlaylistId = currentSection.type === 'playlist' ? currentSection.id : null;
  const { data: playlistTracksData, isLoading: isLoadingPlaylistTracks } = useQuery({
    queryKey: ['player-playlist-tracks', activePlaylistId],
    queryFn: () => (activePlaylistId ? api.getPlayerPlaylistTracks(activePlaylistId) : null),
    enabled: Boolean(activePlaylistId),
  });

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: () => api.scanPlayerLibrary(),
    onSuccess: (data) => {
      showToast(`Đã quét xong: tìm thấy ${data.count} bài hát`);
      queryClient.invalidateQueries({ queryKey: ['player-library'] });
    },
    onError: (err: Error) => {
      showToast(`Lỗi quét thư mục: ${err.message}`);
    },
  });

  // All tracks from library
  const allTracks: PlayerTrack[] = useMemo(() => {
    return libraryData?.tracks || [];
  }, [libraryData]);

  // Tracks for active section
  const sectionTracks: PlayerTrack[] = useMemo(() => {
    if (currentSection.type === 'all') {
      return allTracks;
    }
    if (currentSection.type === 'favorites') {
      return allTracks.filter((t) => t.is_favorite);
    }
    if (currentSection.type === 'playlist') {
      if (!playlistTracksData) return [];
      // Map playlist items to PlayerTrack structure
      return playlistTracksData.map((pt) => {
        const found = allTracks.find((t) => t.path === pt.track_path);
        if (found) return found;
        return {
          path: pt.track_path,
          filename: pt.track_path.split('/').pop() || '',
          title: pt.title,
          artist: pt.artist,
          album: pt.album,
          genre: '',
          year: '',
          duration: pt.duration,
          file_size: 0,
          mtime_ns: 0,
          has_cover_art: pt.has_cover_art,
          is_favorite: pt.is_favorite,
        };
      });
    }
    return allTracks;
  }, [currentSection, allTracks, playlistTracksData]);

  // Filter & Sort
  const filteredAndSortedTracks: PlayerTrack[] = useMemo(() => {
    let result = sectionTracks;

    // Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.artist.toLowerCase().includes(q) ||
          t.album.toLowerCase().includes(q) ||
          t.filename.toLowerCase().includes(q)
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      if (sortOption === 'title_asc') {
        return (a.title || a.filename).localeCompare(b.title || b.filename);
      }
      if (sortOption === 'title_desc') {
        return (b.title || b.filename).localeCompare(a.title || a.filename);
      }
      if (sortOption === 'artist') {
        return (a.artist || '').localeCompare(b.artist || '');
      }
      if (sortOption === 'duration') {
        return (b.duration || 0) - (a.duration || 0);
      }
      if (sortOption === 'recent') {
        return (b.mtime_ns || 0) - (a.mtime_ns || 0);
      }
      return 0;
    });

    return result;
  }, [sectionTracks, searchQuery, sortOption]);

  // Playlist actions
  const handleAddToPlaylist = async (playlistId: number, trackPath: string) => {
    try {
      await api.addTracksToPlayerPlaylist(playlistId, [trackPath]);
      showToast('Đã thêm bài hát vào playlist');
      refetchPlaylists();
      if (activePlaylistId === playlistId) {
        queryClient.invalidateQueries({ queryKey: ['player-playlist-tracks', playlistId] });
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Lỗi khi thêm vào playlist');
    }
  };

  const handleRemoveFromPlaylist = async (trackPath: string) => {
    if (!activePlaylistId) return;
    try {
      await api.removeTrackFromPlayerPlaylist(activePlaylistId, trackPath);
      showToast('Đã xóa bài hát khỏi playlist');
      queryClient.invalidateQueries({ queryKey: ['player-playlist-tracks', activePlaylistId] });
      refetchPlaylists();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Lỗi khi xóa khỏi playlist');
    }
  };

  const handleDeletePlaylist = async (id: number) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa playlist này?')) return;
    try {
      await api.deletePlayerPlaylist(id);
      showToast('Đã xóa playlist');
      refetchPlaylists();
      if (currentSection.type === 'playlist' && currentSection.id === id) {
        setCurrentSection({ type: 'all' });
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Lỗi khi xóa playlist');
    }
  };

  const handleExportM3U = (id: number) => {
    const url = api.exportPlayerPlaylistM3UUrl(id);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `playlist_${id}.m3u8`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Đang tải về file .m3u8');
  };

  const favoritesCount = useMemo(() => allTracks.filter((t) => t.is_favorite).length, [allTracks]);

  return (
    <div className="flex-1 min-h-0 flex overflow-hidden relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-4 right-4 z-50 px-4 py-2 rounded-xl bg-zinc-800 text-white text-xs border border-white/10 shadow-2xl animate-in fade-in slide-in-from-top-2">
          {toastMessage}
        </div>
      )}

      {/* Left Sidebar */}
      <PlayerSidebar
        width={leftWidth}
        currentSection={currentSection}
        onSelectSection={setCurrentSection}
        playlists={playlists}
        favoritesCount={favoritesCount}
        totalTracksCount={allTracks.length}
        onOpenCreatePlaylist={() => {
          setEditingPlaylist(null);
          setPlaylistModalMode('create');
        }}
        onOpenImportM3U={() => {
          setEditingPlaylist(null);
          setPlaylistModalMode('import');
        }}
        onEditPlaylist={(pl) => {
          setEditingPlaylist(pl);
          setPlaylistModalMode('edit');
        }}
        onDeletePlaylist={handleDeletePlaylist}
        onExportM3U={handleExportM3U}
      />

      {/* Left Resizer Handle */}
      <div
        onMouseDown={handleLeftResizeStart}
        onDoubleClick={() => {
          setLeftWidth(240);
          try {
            localStorage.setItem('auralytica_player_left_width', '240');
          } catch {}
        }}
        className="w-1.5 hover:w-2 hover:bg-emerald-500/50 active:bg-emerald-500 cursor-col-resize z-30 transition-all select-none group flex items-center justify-center shrink-0 -mx-0.5"
        title="Kéo để chỉnh độ rộng thư viện (Nhấp đúp để đặt lại 240px)"
      >
        <div className="w-0.5 h-6 bg-white/20 group-hover:bg-white/60 rounded-full transition-colors" />
      </div>

      {/* Center Content Area */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col bg-[#09090b] overflow-hidden">
        {/* Header Bar */}
        <PlayerHeader
          currentFolder={libraryData?.folder || ''}
          onRescan={() => scanMutation.mutate()}
          isScanning={scanMutation.isPending}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          sortOption={sortOption}
          onSortOptionChange={setSortOption}
          totalFilteredTracks={filteredAndSortedTracks.length}
        />

        {/* Tracks List or Empty State */}
        {isLoadingLibrary || (activePlaylistId && isLoadingPlaylistTracks) ? (
          <div className="flex-1 flex items-center justify-center p-12 text-zinc-500">
            <Loader2 className="w-6 h-6 animate-spin mr-2" />
            <span className="text-xs">Đang tải danh sách bài hát...</span>
          </div>
        ) : filteredAndSortedTracks.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-zinc-500 space-y-3">
            {searchQuery ? (
              <>
                <FolderSearch className="w-10 h-10 opacity-40 mx-auto" />
                <p className="text-sm font-medium text-zinc-300">Không tìm thấy bài hát phù hợp</p>
                <p className="text-xs text-zinc-500">
                  Thử tìm kiếm với từ khóa khác hoặc xóa bộ lọc tìm kiếm.
                </p>
              </>
            ) : currentSection.type === 'favorites' ? (
              <>
                <Music className="w-10 h-10 opacity-40 mx-auto text-rose-500/50" />
                <p className="text-sm font-medium text-zinc-300">Chưa có bài hát yêu thích</p>
                <p className="text-xs text-zinc-500">
                  Nhấn vào biểu tượng trái tim ở bất kỳ bài hát nào để đưa vào danh sách này.
                </p>
              </>
            ) : currentSection.type === 'playlist' ? (
              <>
                <Music className="w-10 h-10 opacity-40 mx-auto" />
                <p className="text-sm font-medium text-zinc-300">Playlist này chưa có bài hát</p>
                <p className="text-xs text-zinc-500">
                  Chọn "Thêm vào playlist" từ menu tùy chọn của bài hát bất kỳ để thêm vào đây.
                </p>
              </>
            ) : (
              <>
                <Music className="w-10 h-10 opacity-40 mx-auto" />
                <p className="text-sm font-medium text-zinc-300">Thư mục chưa có bài hát</p>
                <p className="text-xs text-zinc-500">
                  Nhấn "Quét lại" hoặc tải nhạc về từ Takeout Studio.
                </p>
                <button
                  type="button"
                  onClick={() => scanMutation.mutate()}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white transition-all shadow-md mt-2"
                >
                  Quét lại thư viện
                </button>
              </>
            )}
          </div>
        ) : viewMode === 'table' ? (
          <TrackTableView
            tracks={filteredAndSortedTracks}
            playlists={playlists}
            onEditTrack={(track) => setEditingTrack(track)}
            onAddToPlaylist={handleAddToPlaylist}
            onRemoveFromPlaylist={handleRemoveFromPlaylist}
            isPlaylistView={currentSection.type === 'playlist'}
          />
        ) : (
          <TrackGridView
            tracks={filteredAndSortedTracks}
            playlists={playlists}
            onEditTrack={(track) => setEditingTrack(track)}
            onAddToPlaylist={handleAddToPlaylist}
            onRemoveFromPlaylist={handleRemoveFromPlaylist}
            isPlaylistView={currentSection.type === 'playlist'}
          />
        )}
      </div>

      {/* Right Resizer Handle */}
      {rightPanelTab && (
        <div
          onMouseDown={handleRightResizeStart}
          onDoubleClick={() => {
            setRightWidth(320);
            try {
              localStorage.setItem('auralytica_player_right_width', '320');
            } catch {}
          }}
          className="w-1.5 hover:w-2 hover:bg-emerald-500/50 active:bg-emerald-500 cursor-col-resize z-30 transition-all select-none group flex items-center justify-center shrink-0 -mx-0.5"
          title="Kéo để chỉnh độ rộng thông tin (Nhấp đúp để đặt lại 320px)"
        >
          <div className="w-0.5 h-6 bg-white/20 group-hover:bg-white/60 rounded-full transition-colors" />
        </div>
      )}

      {/* Docked Right Sidebar */}
      <PlayerRightSidebar
        width={rightWidth}
        onEditTrack={(track) => setEditingTrack(track)}
        playlists={playlists}
        onAddToPlaylist={handleAddToPlaylist}
      />

      {/* Edit Metadata Modal */}
      {editingTrack && (
        <MetadataEditModal
          track={editingTrack}
          onClose={() => setEditingTrack(null)}
          onSaved={() => {
            showToast('Đã cập nhật thông tin thẻ bài hát');
            refetchLibrary();
          }}
        />
      )}

      {/* Playlist Create/Edit/Import Modal */}
      {playlistModalMode && (
        <PlaylistModal
          mode={playlistModalMode}
          playlist={editingPlaylist}
          onClose={() => setPlaylistModalMode(null)}
          onSaved={(pl) => {
            showToast(`Đã ${playlistModalMode === 'create' ? 'tạo' : 'cập nhật'} playlist "${pl.name}"`);
            refetchPlaylists();
          }}
        />
      )}
    </div>
  );
};
