"""
Data Tool Definitions.

Tools for SQL, DataFrames, Visualization, and Spreadsheets.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ParameterType,
)


class RunSQLQueryTool(BaseTool):
    """Execute SQL queries against databases."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="run_sql_query",
            description="Execute a SQL query against a database",
            category=ToolCategory.DATA,
            tags=["sql", "database", "query", "data"],
            examples=[
                "Run SELECT * FROM users",
                "Query the sales database",
                "Get customer data from database",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                description="SQL query to execute",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="connection_string",
                description="Database connection string",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="parameters",
                description="Query parameters (JSON object)",
                param_type=ParameterType.DICT,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        connection_string = kwargs.get("connection_string")
        params = kwargs.get("parameters", {})

        try:
            from ag3ntwerk.integrations.data.sql import SQLIntegration

            sql = SQLIntegration(connection_string=connection_string)
            result = await sql.execute(query, params)

            return ToolResult(
                success=True,
                data={
                    "rows": result.rows,
                    "columns": result.columns,
                    "row_count": result.row_count,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class AnalyzeDataFrameTool(BaseTool):
    """Analyze data using pandas/polars DataFrames."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="analyze_dataframe",
            description="Load and analyze data from CSV/Excel files",
            category=ToolCategory.DATA,
            tags=["dataframe", "pandas", "analyze", "statistics"],
            examples=[
                "Analyze sales.csv",
                "Get statistics for the data file",
                "Summarize the dataset",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                description="Path to data file (CSV, Excel, JSON)",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="operations",
                description="Operations to perform (describe, head, info, etc.)",
                param_type=ParameterType.ARRAY,
                required=False,
                default=["describe"],
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        operations = kwargs.get("operations", ["describe"])

        try:
            from ag3ntwerk.integrations.data.dataframes import DataFrameIntegration

            df_int = DataFrameIntegration()
            df = await df_int.load(file_path)

            results = {}
            for op in operations:
                if op == "describe":
                    results["describe"] = await df_int.describe(df)
                elif op == "head":
                    results["head"] = await df_int.head(df)
                elif op == "info":
                    results["info"] = await df_int.info(df)
                elif op == "shape":
                    results["shape"] = {"rows": len(df), "columns": len(df.columns)}

            return ToolResult(
                success=True,
                data=results,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class CreateVisualizationTool(BaseTool):
    """Create data visualizations."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_visualization",
            description="Create charts and visualizations from data",
            category=ToolCategory.DATA,
            tags=["chart", "graph", "visualization", "plot"],
            examples=[
                "Create a bar chart of sales",
                "Plot revenue over time",
                "Visualize user growth",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="data_file",
                description="Path to data file",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="chart_type",
                description="Chart type (bar, line, pie, scatter)",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="x_column",
                description="Column for X axis",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="y_column",
                description="Column for Y axis",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="output_path",
                description="Output file path",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="title",
                description="Chart title",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        data_file = kwargs.get("data_file")
        chart_type = kwargs.get("chart_type")
        x_column = kwargs.get("x_column")
        y_column = kwargs.get("y_column")
        output_path = kwargs.get("output_path")
        title = kwargs.get("title", "")

        try:
            from ag3ntwerk.integrations.data.visualization import VisualizationIntegration

            viz = VisualizationIntegration()

            # Create chart based on type
            chart_path = await viz.create_chart(
                data_path=data_file,
                chart_type=chart_type,
                x=x_column,
                y=y_column,
                output_path=output_path,
                title=title,
            )

            return ToolResult(
                success=True,
                data={
                    "chart_path": chart_path,
                    "chart_type": chart_type,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class ReadSpreadsheetTool(BaseTool):
    """Read and manipulate spreadsheets."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_spreadsheet",
            description="Read data from Excel or Google Sheets",
            category=ToolCategory.DATA,
            tags=["spreadsheet", "excel", "sheets", "data"],
            examples=[
                "Read the Excel file",
                "Get data from Google Sheets",
                "Load spreadsheet data",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                description="Path to spreadsheet file or Google Sheets ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="sheet_name",
                description="Sheet name or index",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="range",
                description="Cell range (e.g., A1:D10)",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path")
        sheet_name = kwargs.get("sheet_name")
        cell_range = kwargs.get("range")

        try:
            from ag3ntwerk.integrations.data.spreadsheets import SpreadsheetIntegration

            sheets = SpreadsheetIntegration()
            data = await sheets.read(
                path=file_path,
                sheet=sheet_name,
                range=cell_range,
            )

            return ToolResult(
                success=True,
                data={
                    "rows": data.rows,
                    "columns": data.columns,
                    "row_count": len(data.rows),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
