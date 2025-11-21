"""Rollback system for fine-tuning adjustments."""

from auto_fine_tune import AutoFineTuner

def main():
    """Rollback fine-tuning adjustments if needed."""
    
    print("🔄 FINE-TUNING ROLLBACK SYSTEM")
    print("=" * 60)
    print("This will restore your files to the previous version")
    print("if the fine-tuning adjustments cause any issues.")
    print("=" * 60)
    
    response = input("\n⚠️ Are you sure you want to rollback? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        fine_tuner = AutoFineTuner()
        success = fine_tuner.rollback_changes()
        
        if success:
            print("\n✅ Rollback completed successfully!")
            print("🚀 Restart your bot to apply the rollback.")
        else:
            print("\n❌ Rollback failed or no backups found.")
    else:
        print("\n📋 Rollback cancelled.")

if __name__ == "__main__":
    main()
