import { Component, OnInit, ChangeDetectorRef, HostListener } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { DatePipe, CommonModule } from '@angular/common';
import { environment } from '../../../environments/environment';

interface RecycleBinFile {
  file_id: number;
  file_name: string;
  file_size: number;
  file_type: string;
  deleted_at: string;
}

@Component({
  selector: 'app-recycle-bin',
  imports: [DatePipe, CommonModule],
  templateUrl: './recycle-bin.html',
  styleUrl: './recycle-bin.css'
})
export class RecycleBin implements OnInit {

  recycleBinFiles: RecycleBinFile[] = [];

  showMessage = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  openMenuId: number | null = null;
  menuTop = 0;
  menuLeft = 0;

  showRestorePopup = false;
  selectedRestoreFile: RecycleBinFile | null = null;

  showPermanentDeletePopup = false;
  selectedDeleteFile: RecycleBinFile | null = null;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.getRecycleBinFiles();
  }

  getRecycleBinFiles() {

    this.http.get<RecycleBinFile[]>(
      `${environment.apiUrl}/recycle-bin`
    ).subscribe({

      next: response => {

        this.recycleBinFiles = response;

        this.cdr.detectChanges();
      },

      error: error => {

        console.log(error);

      }

    });
  }

  /* =========================
  FILE TYPE BADGE
  ========================= */

  getFileTypeInfo(fileType: string | null | undefined): { label: string; class: string } {

    const type = (fileType ?? '').toLowerCase();

    if (type.includes('pdf')) return { label: 'PDF', class: 'type-pdf' };
    if (type.includes('word')) return { label: 'DOC', class: 'type-doc' };
    if (type.includes('excel') || type.includes('spreadsheet') || type === 'text/csv') return { label: 'XLS', class: 'type-sheet' };
    if (type.includes('powerpoint') || type.includes('presentation')) return { label: 'PPT', class: 'type-slide' };
    if (type.includes('zip') || type.includes('rar') || type.includes('7z') || type.includes('tar') || type.includes('compressed')) return { label: 'ZIP', class: 'type-archive' };
    if (type.includes('json')) return { label: 'JSON', class: 'type-code' };
    if (type.includes('python')) return { label: 'PY', class: 'type-code' };
    if (type.includes('javascript') || type.includes('typescript')) return { label: 'JS', class: 'type-code' };
    if (type.includes('html')) return { label: 'HTML', class: 'type-code' };
    if (type.includes('css')) return { label: 'CSS', class: 'type-code' };
    if (type.includes('executable') || type.includes('x-msdownload') || type.includes('x-elf')) return { label: 'EXE', class: 'type-exe' };
    if (type.includes('empty')) return { label: 'EMPTY', class: 'type-txt' };
    if (type === 'text/plain') return { label: 'TXT', class: 'type-txt' };

    if (type.startsWith('image/')) return { label: type.split('/')[1].toUpperCase(), class: 'type-image' };
    if (type.startsWith('video/')) return { label: 'VIDEO', class: 'type-default' };
    if (type.startsWith('audio/')) return { label: 'AUDIO', class: 'type-default' };

    const subtype = (type.split('/')[1] || type || 'file').toUpperCase().slice(0, 5);

    return { label: subtype, class: 'type-default' };
  }

  formatFileSize(size: number): string {

    size = Number(size) || 0;

    if (size < 1024) {

      return size + ' B';

    }

    if (size < 1024 * 1024) {

      return (size / 1024).toFixed(2) + ' KB';

    }

    if (size < 1024 * 1024 * 1024) {

      return (size / (1024 * 1024)).toFixed(2) + ' MB';

    }

    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  }

  /* =========================
  DAYS LEFT
  ========================= */

  getDaysLeft(deletedAt: string): number {

    const deletedDate = new Date(deletedAt);
    const expiryDate = new Date(deletedDate);

    expiryDate.setDate(expiryDate.getDate() + 30);

    const diffMs = expiryDate.getTime() - Date.now();

    return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  }

  ViewFile(file: RecycleBinFile) {

    const filename = file.file_name

    this.http.get(
      `${environment.apiUrl}/files/${file.file_id}/view`,
      {
        responseType: 'blob'
      }
    ).subscribe({

      next: response => {

        const fileurl = URL.createObjectURL(response);

        window.open(fileurl);

      },

      error: error => {

        this.showMessagePopup(
          `Failed to Open ${filename}`,
          'error'
        )

        console.log(error);

      }

    });
  }

  /* =========================
  ACTIONS MENU
  ========================= */

  toggleActionMenu(event: MouseEvent, file: RecycleBinFile) {

    event.stopPropagation();

    if (this.openMenuId === file.file_id) {

      this.closeActionMenu();

      return;
    }

    const button = event.currentTarget as HTMLElement;

    const rect = button.getBoundingClientRect();

    const menuHeight = 112;

    const openUp =
      rect.bottom + menuHeight + 8 > window.innerHeight;

    this.menuTop = openUp
      ? rect.top - menuHeight - 6
      : rect.bottom + 6;

    this.menuLeft = Math.max(8, rect.right - 160);

    this.openMenuId = file.file_id;

    this.cdr.detectChanges();
  }

  @HostListener('document:click')
  @HostListener('document:keydown.escape')
  @HostListener('window:resize')
  closeActionMenu() {

    if (this.openMenuId === null) {

      return;
    }

    this.openMenuId = null;

    this.cdr.detectChanges();
  }

  runRecycleBinAction(action: string, file: RecycleBinFile) {

    this.closeActionMenu();

    if (action === 'restore') {

      this.openRestorePopup(file);

    }

    if (action === 'permanent-delete') {

      this.openPermanentDeletePopup(file);

    }
  }

  /* =========================
  RESTORE
  ========================= */

  openRestorePopup(file: RecycleBinFile) {

    this.selectedRestoreFile = file;

    this.showRestorePopup = true;

    this.cdr.detectChanges();
  }

  closeRestorePopup() {

    this.showRestorePopup = false;

    this.selectedRestoreFile = null;

    this.cdr.detectChanges();
  }

  restoreFile() {

    if (!this.selectedRestoreFile) {

      return;
    }

    const fileId = this.selectedRestoreFile.file_id;

    const filename = this.selectedRestoreFile.file_name;

    this.http.patch(
      `${environment.apiUrl}/recycle-bin/${fileId}/restore`,
      {}
    ).subscribe({

      next: response => {

        this.recycleBinFiles = this.recycleBinFiles.filter(
          file => file.file_id !== fileId
        );

        this.closeRestorePopup();

        this.showMessagePopup(
          `${filename} restored to My Files`
        );

      },

      error: error => {

        this.closeRestorePopup();

        this.showMessagePopup(
          `Failed to restore ${filename}`,
          'error'
        );

      }

    });
  }

  /* =========================
  PERMANENT DELETE
  ========================= */

  openPermanentDeletePopup(file: RecycleBinFile) {

    this.selectedDeleteFile = file;

    this.showPermanentDeletePopup = true;

    this.cdr.detectChanges();
  }

  closePermanentDeletePopup() {

    this.showPermanentDeletePopup = false;

    this.selectedDeleteFile = null;

    this.cdr.detectChanges();
  }

  permanentlyDeleteFile() {

    if (!this.selectedDeleteFile) {

      return;
    }

    const fileId = this.selectedDeleteFile.file_id;

    const filename = this.selectedDeleteFile.file_name;

    this.http.delete(
      `${environment.apiUrl}/recycle-bin/${fileId}/permanent-delete`
    ).subscribe({

      next: response => {

        this.recycleBinFiles = this.recycleBinFiles.filter(
          file => file.file_id !== fileId
        );

        this.closePermanentDeletePopup();

        this.showMessagePopup(
          `${filename} permanently deleted`
        );

      },

      error: error => {

        this.closePermanentDeletePopup();

        this.showMessagePopup(
          `Failed to permanently delete ${filename}`,
          'error'
        );

      }

    });
  }

  showMessagePopup(
    text: string,
    type: 'success' | 'error' = 'success'
  ) {

    this.message = text;

    this.messageType = type;

    this.showMessage = true;

    this.cdr.detectChanges();

    setTimeout(() => {

      this.showMessage = false;

      this.cdr.detectChanges();

    }, 3000);
  }

}