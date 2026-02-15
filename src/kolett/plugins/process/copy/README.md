# Copy Process Plugin

The **Copy** plugin is the default file handler for Kolett. It performs a standard file copy from source to destination using Python's `shutil.copy2`, which ensures that file metadata (such as timestamps) is preserved where possible.

## 🛠 Features
- **Metadata Preservation**: Uses `shutil.copy2` to keep track of creation and modification times.
- **Directory Auto-Creation**: Automatically creates the target directory structure if it doesn't exist.
- **Dry Run Support**: Logs the intended copy operation without touching the filesystem.

## 📝 Configuration
This plugin is typically invoked by the engine for every file collected from an item's source path.

```yaml
# Example Item configuration in Grist/JSON
process_method: "copy"
target_template: "{{ item_id }}/{{ src_name }}"
```

##  JFS/NFS Performance
Since Kolett is designed to run on the **Mothership Gateway** (NFS over JuiceFS), this plugin benefits from the local cache and asynchronous writes configured in the studio's infrastructure.