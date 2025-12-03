"""CLI commands for data retention management."""

import click
from app.services.data_retention import data_retention_service


def register_cli_commands(app):
    """Register data retention CLI commands with Flask app."""

    @app.cli.group()
    def retention():
        """Data retention management commands."""
        pass

    @retention.command()
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be deleted without actually deleting",
    )
    @click.option(
        "--type",
        "cleanup_type",
        type=click.Choice(["all", "check_results", "incidents", "notification_logs"]),
        default="all",
        help="Type of data to clean up",
    )
    @click.option("--days", type=int, help="Override retention days")
    def cleanup(dry_run, cleanup_type, days):
        """Clean up old monitoring data."""
        click.echo("Data Retention Cleanup")
        click.echo("=" * 30)

        try:
            # Get current database stats
            click.echo("\nCurrent database statistics:")
            stats = data_retention_service.get_database_stats()
            for data_type, info in stats.items():
                if isinstance(info, dict) and "total_count" in info:
                    click.echo(f"  {data_type}: {info['total_count']:,} records")

            # Get retention policies
            click.echo("\nCurrent retention policies:")
            for (
                data_type,
                days_count,
            ) in data_retention_service.retention_policies.items():
                click.echo(f"  {data_type}: {days_count} days")

            if dry_run:
                click.echo("\nEstimating cleanup impact (dry run):")
                estimate = data_retention_service.estimate_cleanup_impact()
                total_deletions = estimate["total_estimated_deletions"]

                for data_type, info in estimate["estimated_deletions"].items():
                    count = info["count"]
                    if count > 0:
                        click.echo(
                            f"  Would delete {count:,} {data_type} (older than {info['retention_days']} days)"
                        )

                if total_deletions == 0:
                    click.echo("  No records would be deleted")
                else:
                    click.echo(f"\nTotal estimated deletions: {total_deletions:,}")
            else:
                if days:
                    click.echo(f"\nUsing custom retention: {days} days")

                click.echo(f"\nStarting cleanup for: {cleanup_type}")

                if cleanup_type == "all":
                    result = data_retention_service.cleanup_all_old_data()
                    if result["success"]:
                        click.echo("✓ Cleanup completed successfully")
                        click.echo(
                            f"  Total records deleted: {result['total_deleted']:,}"
                        )

                        for data_type, info in result["results"].items():
                            deleted = info["deleted_count"]
                            if deleted > 0:
                                click.echo(f"  {data_type}: {deleted:,} deleted")
                    else:
                        click.echo(
                            f"✗ Cleanup failed: {result.get('error', 'Unknown error')}"
                        )
                else:
                    # Clean up specific type
                    deleted = 0
                    info = {}
                    if cleanup_type == "check_results":
                        deleted, info = (
                            data_retention_service.cleanup_old_check_results(days)
                        )
                    elif cleanup_type == "incidents":
                        deleted, info = data_retention_service.cleanup_old_incidents(
                            days
                        )
                    elif cleanup_type == "notification_logs":
                        deleted, info = (
                            data_retention_service.cleanup_old_notification_logs(days)
                        )

                    if deleted > 0:
                        click.echo(f"✓ Deleted {deleted:,} {cleanup_type}")
                        click.echo(f"  Retention period: {info['retention_days']} days")
                        click.echo(f"  Records before: {info['total_before']:,}")
                        click.echo(f"  Records after: {info['total_after']:,}")
                    else:
                        click.echo(f"No {cleanup_type} to delete")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    @retention.command()
    def stats():
        """Show database statistics."""
        try:
            stats = data_retention_service.get_database_stats()

            click.echo("Database Statistics")
            click.echo("=" * 20)

            for data_type, info in stats.items():
                if isinstance(info, dict) and "total_count" in info:
                    click.echo(f"\n{data_type.replace('_', ' ').title()}:")
                    click.echo(f"  Total records: {info['total_count']:,}")

                    if "oldest_record" in info and info["oldest_record"]:
                        click.echo(f"  Oldest record: {info['oldest_record']}")
                    if "newest_record" in info and info["newest_record"]:
                        click.echo(f"  Newest record: {info['newest_record']}")

                    if "active_count" in info:
                        click.echo(f"  Active count: {info['active_count']:,}")

            # Show deduplication statistics
            click.echo("\nDeduplication Statistics:")
            click.echo("-" * 25)

            try:
                # Import here to avoid circular imports
                from app.services.deduplication import deduplication_service

                dedup_stats = deduplication_service.get_deduplication_stats()

                if "error" in dedup_stats:
                    click.echo(
                        f"  Error getting deduplication stats: {dedup_stats['error']}"
                    )
                    return

                # Error Messages
                if "error_messages" in dedup_stats:
                    stats = dedup_stats["error_messages"]
                    click.echo("\nError Messages:")
                    click.echo(f"  Unique entries: {stats['unique_messages']:,}")
                    click.echo(f"  Total uses: {stats['total_uses']:,}")
                    if stats["total_uses"] > 0:
                        ratio = (
                            stats["total_uses"] / stats["unique_messages"]
                            if stats["unique_messages"] > 0
                            else 1
                        )
                        click.echo(f"  Deduplication ratio: {ratio:.1f}x")
                        click.echo(f"  Space saved: {stats['deduplication_ratio']}")

                # TLS Certificates
                if "tls_certificates" in dedup_stats:
                    stats = dedup_stats["tls_certificates"]
                    click.echo("\nTLS Certificates:")
                    click.echo(f"  Unique certificates: {stats['unique_certs']:,}")
                    click.echo(f"  Total uses: {stats['total_uses']:,}")
                    if stats["total_uses"] > 0:
                        ratio = (
                            stats["total_uses"] / stats["unique_certs"]
                            if stats["unique_certs"] > 0
                            else 1
                        )
                        click.echo(f"  Deduplication ratio: {ratio:.1f}x")
                        click.echo(f"  Space saved: {stats['deduplication_ratio']}")

                # Domain Info
                if "domain_info" in dedup_stats:
                    stats = dedup_stats["domain_info"]
                    click.echo("\nDomain Info:")
                    click.echo(f"  Unique domains: {stats['unique_domains']:,}")
                    click.echo(f"  Total uses: {stats['total_uses']:,}")
                    if stats["total_uses"] > 0:
                        ratio = (
                            stats["total_uses"] / stats["unique_domains"]
                            if stats["unique_domains"] > 0
                            else 1
                        )
                        click.echo(f"  Deduplication ratio: {ratio:.1f}x")
                        click.echo(f"  Space saved: {stats['deduplication_ratio']}")

                # Overview
                if "overview" in dedup_stats:
                    overview = dedup_stats["overview"]
                    click.echo("\nDeduplication Overview:")
                    click.echo(
                        f"  Total check results: {overview['total_check_results']:,}"
                    )
                    click.echo(
                        f"  Reference records: {overview['reference_records']:,}"
                    )

            except Exception as e:
                click.echo(f"  Error getting deduplication stats: {e}")

            # Show retention policies
            click.echo("\nRetention Policies:")
            for data_type, days in data_retention_service.retention_policies.items():
                click.echo(f"  {data_type}: {days} days")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    @retention.command()
    @click.argument("data_type")
    @click.argument("days", type=int)
    def set_policy(data_type, days):
        """Set retention policy for a data type."""
        valid_types = ["check_results", "incidents", "notification_logs"]

        if data_type not in valid_types:
            click.echo(f"Invalid data type. Valid options: {', '.join(valid_types)}")
            raise click.Abort()

        if days < 1:
            click.echo("Retention days must be at least 1")
            raise click.Abort()

        try:
            data_retention_service.set_retention_policy(data_type, days)
            click.echo(f"✓ Set retention policy for {data_type} to {days} days")
            click.echo("\nCurrent policies:")
            for dt, d in data_retention_service.retention_policies.items():
                click.echo(f"  {dt}: {d} days")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    @retention.command()
    def estimate():
        """Estimate cleanup impact without deleting."""
        try:
            estimate = data_retention_service.estimate_cleanup_impact()

            click.echo("Cleanup Impact Estimation")
            click.echo("=" * 25)

            total_deletions = estimate["total_estimated_deletions"]

            if total_deletions == 0:
                click.echo("No records would be deleted")
            else:
                click.echo(f"Total estimated deletions: {total_deletions:,}\n")

                for data_type, info in estimate["estimated_deletions"].items():
                    count = info["count"]
                    if count > 0:
                        click.echo(f"{data_type.replace('_', ' ').title()}:")
                        click.echo(f"  Records to delete: {count:,}")
                        click.echo(f"  Retention period: {info['retention_days']} days")
                        click.echo(f"  Cutoff date: {info['cutoff_date']}")
                        click.echo()

            click.echo("(Use --dry-run with cleanup command for more details)")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()
