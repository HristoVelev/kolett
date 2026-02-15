# Symlink Process Plugin

The **Symlink** plugin allows Kolett to create symbolic links at the destination pointing back to the source files, rather than performing a physical data copy. This is ideal for internal studio handoffs, "virtual" deliveries, or any scenario where saving disk space and ensuring zero-latency "delivery" is required.

## 🛠 Features
- **Zero Storage Overhead**: No data is duplicated.
- **Instantaneous**: The delivery happens at the speed of the filesystem metadata update.
- **Auto-Cleanup**: If a file or link already exists at the target path, it is unlinked before the new symlink is created.
- **Dry Run Support**: Logs the intended link operation without touching the filesystem.

## 📝 Configuration
This plugin is invoked by setting the `process_method` in your item configuration.

```yaml
# Example Item configuration in Grist/JSON
process_method: "symlink"
target_template: "internal_review/{{ src_name }}"
```

## ⚠️ Important Considerations
- **Permissions**: Ensure the user running Kolett has permission to create symlinks on the target filesystem.
- **Broken Links**: If the source files are moved or deleted, the symlinks in the delivery folder will break.
- **Client Deliveries**: Do not use this method for external client deliveries (e.g., SFTP/Aspera), as symlinks generally cannot be resolved outside of the local network.