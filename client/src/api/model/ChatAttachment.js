/**
 * Chat Attachment Model
 * 
 * Represents a file attached to a chat or message with file metadata and base64 data.
 * Corresponds to the Python ChatAttachment model.
 */
export class ChatAttachment {
  constructor(options = {}) {
    this.file_name = options.file_name || ''
    this.file_type = options.file_type || 'application/octet-stream'
    this.file_size = options.file_size || 0
    this.base64_data = options.base64_data || ''
    this.uploaded_at = options.uploaded_at || new Date().toISOString()
  }

  isValid() {
    return this.file_name && this.file_type && this.base64_data
  }

  getValidationErrors() {
    const errors = []
    if (!this.file_name || this.file_name.trim().length === 0) {
      errors.push('File name is required')
    }
    if (!this.file_type || this.file_type.trim().length === 0) {
      errors.push('File type is required')
    }
    if (!this.base64_data || this.base64_data.trim().length === 0) {
      errors.push('File data is required')
    }
    if (this.file_size <= 0) {
      errors.push('File size must be greater than 0')
    }
    return errors
  }

  getExtension() {
    const parts = this.file_name.split('.')
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
  }

  isImage() {
    return this.file_type.startsWith('image/')
  }

  isDocument() {
    const docTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument']
    return docTypes.some(type => this.file_type.includes(type))
  }

  getFormattedSize() {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = this.file_size
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  static formatSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  toJSON() {
    return {
      file_name: this.file_name,
      file_type: this.file_type,
      file_size: this.file_size,
      base64_data: this.base64_data,
      uploaded_at: this.uploaded_at
    }
  }

  static fromJSON(json) {
    return new ChatAttachment(json)
  }

  static async fromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const base64Data = e.target.result.split(',')[1]
        resolve(new ChatAttachment({
          file_name: file.name,
          file_type: file.type || 'application/octet-stream',
          file_size: file.size,
          base64_data: base64Data,
          uploaded_at: new Date().toISOString()
        }))
      }
      reader.onerror = (err) => reject(err)
      reader.readAsDataURL(file)
    })
  }

  clone() {
    return new ChatAttachment(this.toJSON())
  }
}

export default ChatAttachment