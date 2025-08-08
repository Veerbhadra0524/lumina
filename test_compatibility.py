import os
import json
from datetime import datetime

def analyze_directory_structure():
    """Analyze current project structure"""
    
    structure = {}
    important_dirs = [
        "data", "modules", "templates", "static", 
        "logs", "blueprints", "lum_env"
    ]
    
    for dir_name in important_dirs:
        if os.path.exists(dir_name):
            structure[dir_name] = analyze_folder(dir_name)
    
    # Analyze root files
    root_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    structure['root_files'] = root_files
    
    return structure

def analyze_folder(folder_path, max_depth=2, current_depth=0):
    """Recursively analyze folder structure"""
    if current_depth >= max_depth:
        return {"truncated": True}
    
    try:
        contents = {"files": [], "folders": {}, "total_size_mb": 0}
        
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            
            if os.path.isfile(item_path):
                size_mb = round(os.path.getsize(item_path) / 1024 / 1024, 2)
                contents["files"].append({
                    "name": item,
                    "size_mb": size_mb
                })
                contents["total_size_mb"] += size_mb
                
            elif os.path.isdir(item_path):
                subfolder_info = analyze_folder(item_path, max_depth, current_depth + 1)
                contents["folders"][item] = subfolder_info
                contents["total_size_mb"] += subfolder_info.get("total_size_mb", 0)
        
        contents["total_size_mb"] = round(contents["total_size_mb"], 2)
        return contents
        
    except PermissionError:
        return {"error": "Permission denied"}
    except Exception as e:
        return {"error": str(e)}

def identify_safe_to_delete():
    """Identify files/folders safe to delete"""
    safe_to_delete = {
        "temporary_folders": [],
        "log_files": [],
        "cache_files": [],
        "upload_folders": []
    }
    
    # Check data/uploads for old uploads
    uploads_path = "data/uploads"
    if os.path.exists(uploads_path):
        for user_folder in os.listdir(uploads_path):
            user_path = os.path.join(uploads_path, user_folder)
            if os.path.isdir(user_path):
                folder_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(user_path)
                    for filename in filenames
                ) / 1024 / 1024
                
                safe_to_delete["upload_folders"].append({
                    "path": user_path,
                    "size_mb": round(folder_size, 2),
                    "reason": "Uploaded files can be cleaned after processing"
                })
    
    # Check for large log files
    if os.path.exists("logs"):
        for log_file in os.listdir("logs"):
            log_path = os.path.join("logs", log_file)
            if os.path.isfile(log_path):
                size_mb = os.path.getsize(log_path) / 1024 / 1024
                if size_mb > 10:  # Large log files
                    safe_to_delete["log_files"].append({
                        "path": log_path,
                        "size_mb": round(size_mb, 2),
                        "reason": "Large log file can be truncated"
                    })
    
    return safe_to_delete

if __name__ == "__main__":
    print("🔍 Analyzing Lumina RAG Directory Structure...")
    
    structure = analyze_directory_structure()
    safe_to_delete = identify_safe_to_delete()
    
    report = {
        "analysis_date": datetime.now().isoformat(),
        "directory_structure": structure,
        "safe_to_delete": safe_to_delete,
        "recommendations": {
            "cleanup_uploads": "data/uploads contains processed files that can be cleaned",
            "optimize_vector_store": "data/vector_store should be user-separated",
            "manage_logs": "Consider rotating log files in logs/",
            "cache_management": "data/vector_store/embedding_cache can grow large"
        }
    }
    
    # Save report
    with open("directory_analysis.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print("✅ Analysis complete! Report saved to 'directory_analysis.json'")
    
    # Print summary
    total_size = sum(
        folder_info.get("total_size_mb", 0) 
        for folder_info in structure.values()
        if isinstance(folder_info, dict)
    )
    
    print(f"\n📊 Summary:")
    print(f"   Total analyzed size: {total_size:.1f} MB")
    print(f"   Upload folders: {len(safe_to_delete['upload_folders'])}")
    print(f"   Large log files: {len(safe_to_delete['log_files'])}")
    
    # Show largest folders
    print(f"\n📁 Largest folders:")
    folder_sizes = [
        (name, info.get("total_size_mb", 0))
        for name, info in structure.items()
        if isinstance(info, dict) and info.get("total_size_mb", 0) > 0
    ]
    folder_sizes.sort(key=lambda x: x[1], reverse=True)
    
    for folder, size in folder_sizes[:5]:
        print(f"   {folder}: {size:.1f} MB")
