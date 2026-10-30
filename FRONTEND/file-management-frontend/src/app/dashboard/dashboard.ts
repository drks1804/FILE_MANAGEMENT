import { Component, OnInit, ChangeDetectorRef, ViewChild} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router';
import { MyFiles } from './my-files/my-files';
import { AuthService } from '../auth/auth';
import { environment } from '../../environments/environment';

interface UploadInitResponse {
  file_id: number;
  upload_id: number;
  s3_upload_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  is_indexed: boolean;
  upload_status: string;
}

interface UploadedPart {
  PartNumber: number;
  ETag: string;
  Size: number;
}

interface UploadedPartsResponse {
  file_id: number;
  upload_id: number;
  uploaded_parts: UploadedPart[];
}

interface IncompleteUpload {
  file_id: number;
  upload_id: number;
  file_name: string;
  file_size: number;
  uploaded_size: number;
  upload_status: string;
}

@Component({
  selector: 'app-dashboard',
  imports: [
    RouterLink,
    RouterLinkActive,
    RouterOutlet
  ],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {

  @ViewChild(RouterOutlet)
  routerOutlet!:RouterOutlet

  showMessage = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  incompleteUploads: IncompleteUpload[] = [];

  uploadInterrupted = false;
  interruptedFileId: number | null = null;
  interruptedFileName = '';
  interruptedProgress = 0;
  uploadingFileName = '' 

  differentFilePopup = false;
  selectedFileName = '';
  selectedFile: File | null = null

  isUploading = false

  firstName = localStorage.getItem('first_name') || '';

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private authservice: AuthService
  ) {}

  ngOnInit(): void {
    this.getIncompleteUploads();
  }

  getIncompleteUploads(): void {
    this.http.get<IncompleteUpload[]>(
      `${environment.apiUrl}/files/incomplete`
    ).subscribe({
      next: (response) => {
        this.incompleteUploads = response;

        console.log(
          'Incomplete uploads:',
          this.incompleteUploads
        );

        // No incomplete uploads: close the popup and return.
        if (this.incompleteUploads.length === 0) {
          this.uploadInterrupted = false;
          this.interruptedFileId = null;
          this.interruptedFileName = '';
          this.interruptedProgress = 0;
          return;
        }

        // Select the first incomplete upload.
        const upload = this.incompleteUploads[0];

        this.interruptedFileId = upload.file_id;
        this.interruptedFileName = upload.file_name;
        this.interruptedProgress = 0;

        // Get the actual uploaded parts from the backend.
        this.getUploadedParts(upload.file_id).subscribe({
          next: (partsResponse) => {
            let uploadedBytes = 0;

            for (const part of partsResponse.uploaded_parts) {
              uploadedBytes += part.Size;
            }

            if (upload.file_size > 0) {
              this.interruptedProgress = Math.min(
                100,
                Math.floor(
                  (uploadedBytes / upload.file_size) * 100
                )
              );
            } else {
              this.interruptedProgress = 0;
            }

            // Open the popup after calculating progress.
            this.uploadInterrupted = true;

            console.log(
              'Uploaded bytes:',
              uploadedBytes,
              'Progress:',
              this.interruptedProgress + '%'
            );
          },
          error: (error) => {
            console.error(
              'Failed to retrieve uploaded parts:',
              error
            );

            this.interruptedProgress = 0;
            this.uploadInterrupted = true;
          }
        });
      },
      error: (error) => {
        console.error(
          'Failed to fetch incomplete uploads:',
          error
        );
      }
    });
  }

  UploadFile(event: Event, selectedFile?: File): void {
    const input = event.target as HTMLInputElement;
    let file: File | undefined = selectedFile;

    // Normal upload: get the file from the file input.
    // Retry: use the file passed by retryInterruptedUpload().
    if (!file) {
      if (!input.files || input.files.length === 0) {
        return;
      }

      file = input.files[0];
    }

    // When retrying an interrupted upload, compare the selected file.
    if (selectedFile && this.interruptedFileId !== null) {
      if (selectedFile.name !== this.interruptedFileName) {
        // Keep the selected File object so Continue can upload this exact file.
        this.selectedFile = selectedFile;
        this.selectedFileName = selectedFile.name;
        this.differentFilePopup = true;
        this.cdr.detectChanges
        return;
      }

      const interruptedId = this.interruptedFileId;
      this.uploadInterrupted = false;
      this.uploadAllParts(selectedFile, interruptedId, input);
      return;
    }

    // Check whether an incomplete upload with the same name and size exists.
    let existingUpload: IncompleteUpload | undefined;

    for (const upload of this.incompleteUploads) {
      if (
        upload.file_name === file.name &&
        upload.file_size === file.size
      ) {
        existingUpload = upload;
        break;
      }
    }

    console.log('Matching incomplete upload:', existingUpload);

    if (existingUpload) {
      console.log('Resuming existing upload:', existingUpload);
      this.uploadAllParts(file, existingUpload.file_id, input);
      return;
    }

    // No matching incomplete upload: initialize a new upload.
    this.startNewUpload(file, input);
  }

  uploadFilePart(
    file: File,
    fileId: number,
    partNumber: number,
    start: number,
    end: number
  ) {
    const chunk = file.slice(start, end);
    const formdata = new FormData();

    formdata.append(
      'chunk',
      chunk,
      file.name
    );

    return this.http.post(
      `${environment.apiUrl}/files/${fileId}/parts?part_number=${partNumber}`,
      formdata
    );
  }

  uploadAllParts(
    file: File,
    fileId: number,
    input: HTMLInputElement
  ): void {

  this.isUploading = true;
  this.cdr.detectChanges()

  this.interruptedFileName = file.name;
  this.interruptedProgress = 0;
  this.cdr.detectChanges()

  console.log('Upload progress visible:', this.isUploading);

    const chunkSize = 5 * 1024 * 1024;
    let uploadedBytes = 0;

    this.getUploadedParts(fileId).subscribe({
      next: (response) => {
        const uploadedPartNumbers = new Set<number>();

        for (const part of response.uploaded_parts) {
          uploadedPartNumbers.add(part.PartNumber);
          uploadedBytes += part.Size;
        }

        this.interruptedProgress = file.size > 0
          ? Math.min(
              100,
              Math.floor((uploadedBytes / file.size) * 100)
            )
          : 0;
          this.cdr.detectChanges()

        console.log(
          'Parts already uploaded:',
          Array.from(uploadedPartNumbers)
        );

        let partNumber = 1;

        const uploadNextPart = (): void => {
          if (partNumber > Math.ceil(file.size / chunkSize)) {
            console.log('All parts uploaded successfully');

            this.completeUpload(
              fileId,
              file.name,
              input
            );
            return;
          }

          const start = (partNumber - 1) * chunkSize;
          const end = Math.min(
            start + chunkSize,
            file.size
          );

          const currentPartNumber = partNumber;

          // Skip parts that have already been uploaded.
          if (uploadedPartNumbers.has(currentPartNumber)) {
            console.log(
              `Skipping already uploaded part ${currentPartNumber}`
            );

            partNumber++;
            uploadNextPart();
            return;
          }

          this.uploadFilePart(
            file,
            fileId,
            currentPartNumber,
            start,
            end
          ).subscribe({
            next: (partResponse) => {
              console.log(
                `Part ${currentPartNumber} uploaded`,
                partResponse
              );

              uploadedBytes += end - start;

              this.interruptedProgress = file.size > 0
                ? Math.min(
                    100,
                    Math.floor((uploadedBytes / file.size) * 100)
                  )
                : 0;
                this.cdr.detectChanges()

              partNumber++;
              uploadNextPart();
            },
            error: (error) => {
              console.error(
                'Upload interrupted:',
                error
              );

              this.interruptedFileId = fileId;
              this.interruptedFileName = file.name;

              this.interruptedProgress = file.size > 0
                ? Math.min(
                    100,
                    Math.floor((uploadedBytes / file.size) * 100)
                  )
                : 0;
                this.cdr.detectChanges()
              this.isUploading = false
              this.uploadInterrupted = true;
            }
          });
        };

        uploadNextPart();
      },
      error: (error) => {
        console.error(
          'Failed to fetch uploaded parts:',
          error
        );

        this.showMessagePopup(
          'Could not check upload progress.',
          'error'
        );
      }
    });
  }

  getUploadedParts(fileId: number) {
    return this.http.get<UploadedPartsResponse>(
      `${environment.apiUrl}/files/${fileId}/parts`
    );
  }

  retryInterruptedUpload(): void {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';

    fileInput.onchange = () => {
      if (!fileInput.files || fileInput.files.length === 0) {
        return;
      }

      const file = fileInput.files[0];

      if (this.interruptedFileId === null) {
        return;
      }

      if (file.name !== this.interruptedFileName) {
        this.selectedFile = file;
        this.selectedFileName = file.name;
        this.differentFilePopup = true;
        this.cdr.detectChanges()
        return;
      }

      this.selectedFile = null;
      this.differentFilePopup = false;

      this.UploadFile(
        { target: fileInput } as unknown as Event,
        file
      );
    };

    fileInput.click();
  }

  cancelInterruptedUpload(): void {
    if (this.interruptedFileId === null) {
      return;
    }

    const fileId = this.interruptedFileId;

    this.http.delete(
      `${environment.apiUrl}/files/${fileId}/cancel`
    ).subscribe({
      next: (response) => {
        console.log('Upload cancelled:', response);

        this.uploadInterrupted = false;
        this.interruptedFileId = null;
        this.interruptedFileName = '';
        this.interruptedProgress = 0;

        this.getIncompleteUploads();

        this.showMessagePopup(
          'Upload cancelled successfully.',
          'success'
        );
      },
      error: (error) => {
        console.error(
          'Failed to cancel upload:',
          error
        );

        this.showMessagePopup(
          'Could not cancel the upload. Please try again.',
          'error'
        );
      }
    });
  }

  chooseCorrectFile(): void {
    // Preserve the interrupted upload and let the user choose again.
    this.differentFilePopup = false;
    this.selectedFile = null;
    this.selectedFileName = '';
    this.retryInterruptedUpload();
  }

  continueWithNewFile(): void {
    const fileId = this.interruptedFileId;
    const newFile = this.selectedFile;

    if (fileId === null || newFile === null) {
      return;
    }

    // Delete the interrupted upload first. Only upload the new file if
    // the backend confirms that cleanup succeeded.
    this.http.delete(
      `${environment.apiUrl}/files/${fileId}/cancel`
    ).subscribe({
      next: () => {
        this.differentFilePopup = false;
        this.uploadInterrupted = false;

        this.interruptedFileId = null;
        this.interruptedFileName = '';
        this.interruptedProgress = 0;


        this.incompleteUploads = this.incompleteUploads.filter(
          upload => upload.file_id !== fileId
        );

        this.selectedFile = null;
        this.selectedFileName = '';

        // Start uploading the exact File object chosen before confirmation.
        this.startNewUpload(newFile);

        // Refresh the list of remaining interrupted uploads.
        this.getIncompleteUploads();
      },
      error: (error) => {
        console.error('Failed to delete interrupted upload:', error);

        // Keep the confirmation popup and selected file so the user can retry.
        this.showMessagePopup(
          'Could not delete the interrupted upload. The new file was not uploaded.',
          'error'
        );
      }
    });
  }


  private startNewUpload(
    file: File,
    input: HTMLInputElement = document.createElement('input')
  ): void {
    const uploadData = {
      file_name: file.name,
      file_size: file.size,
      file_type: file.type || 'application/octet-stream'
    };

    console.log('Browser-reported file type:', file.type);

    this.http.post<UploadInitResponse>(
      `${environment.apiUrl}/files/upload`,
      uploadData
    ).subscribe({
      next: (response) => {
        console.log('New upload initialized:', response);

        this.uploadAllParts(file, response.file_id, input);
      },
      error: (error) => {
        console.error('Upload initialization failed:', error);

        this.showMessagePopup(
          `Could not start uploading ${file.name}. Please try again.`,
          'error'
        );
      }
    });
  }


  completeUpload(
    fileId: number,
    fileName: string,
    input: HTMLInputElement
  ): void {
    this.http.post(
      `${environment.apiUrl}/files/${fileId}/complete`,
      {}
    ).subscribe({
      next: (response) => {
        console.log('Upload completed:', response);
        this.isUploading = false

        input.value = '';

        this.uploadInterrupted = false;
        this.interruptedFileId = null;
        this.interruptedFileName = '';
        this.interruptedProgress = 0;


        this.getIncompleteUploads();

        this.showMessagePopup(
          `${fileName} uploaded successfully`,
          'success'
        );

        const outletComponent = this.routerOutlet?.component;

        if (outletComponent instanceof MyFiles) {
          outletComponent.getFiles();
        }

      },
      error: (error) => {
        this.isUploading=false
        console.error(
          'Upload completion failed:',
          error
        );

        this.showMessagePopup(
          'File upload completion failed. Try again.',
          'error'
        );
      }
    });
  }

  openProfile(): void {
    sessionStorage.setItem(
      'prevurl',
      this.router.url
    );

    this.router.navigate(['/profile']);
  }

  logout(): void {
    this.http.post(
      `${environment.apiUrl}/auth/logout`,
      {},
      {
        withCredentials: true
      }
    ).subscribe({
      next: () => {
        this.authservice.clearAccessToken();

        localStorage.removeItem('first_name');
        localStorage.removeItem('email');

        sessionStorage.removeItem('prevurl');

        this.router.navigate(['/login']);
      }
    });
  }

  showMessagePopup(
    text: string,
    type: 'success' | 'error' = 'success'
  ): void {
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