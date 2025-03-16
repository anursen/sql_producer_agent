import pandas as pd
from config import config
from pydantic import BaseModel, Field
from typing import Optional

class DatabaseDictionaryEntry(BaseModel):
    """Pydantic model for database dictionary entries
    
    Represents a single entry from the database data dictionary,
    typically containing field descriptions and additional metadata
    about database columns/tables.
    """
    field_description: Optional[str] = Field(
        None, 
        description="Detailed description of the database field/column"
    )
    metadata_value: Optional[str] = Field(
        None, 
        description="Additional metadata or specifications for the database field"
    )
    
    class Config:
        allow_none = True
        frozen = True

def get_db_field_definition(field_name: str) -> DatabaseDictionaryEntry:
    """
    Retrieve the database field definition from the data dictionary
    
    Looks up a database field's metadata and description from the data dictionary
    file (Excel/CSV). The dictionary should contain field names in the first column,
    descriptions in the second, and additional metadata in the third.
    
    Args:
        field_name: Name of the database field to look up
        
    Returns:
        DatabaseDictionaryEntry: Field description and metadata from the data dictionary
        
    Example:
        >>> field_info = get_db_field_definition("customer_id")
        >>> print(field_info.field_description)
        "Unique identifier for the customer table"
    """
    tool_config = config.tool_get_data_dictionary
    file_path = tool_config['file_path']
    
    # Read file based on extension
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    # Filter data
    filtered_data = df.iloc[
        df.loc[:, tool_config['filter_column']] == field_name,
        tool_config['return_columns']
    ]
    
    if filtered_data.empty:
        return DatabaseDictionaryEntry()
    
    # Get column names for the selected columns
    selected_columns = df.columns[tool_config['return_columns']]
    
    # Create dictionary with descriptive keys and create Pydantic model
    data_dict = dict(zip(['field_description', 'metadata_value'], filtered_data.iloc[0]))
    return DatabaseDictionaryEntry(**data_dict)