from typing import Any, List, Dict

import numpy as np
import pandas as pd
import pytest

from hamilton import function_modifiers, models, function_modifiers_base
from hamilton import node
from hamilton.function_modifiers import does, ensure_function_empty, InvalidDecoratorException
from hamilton.node import DependencyType


def test_parametrized_invalid_params():
    annotation = function_modifiers.parametrized(
        parameter='non_existant',
        assigned_output={('invalid_node_name', 'invalid_doc'): 'invalid_value'}
    )

    def no_param_node():
        pass

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(no_param_node)

    def wrong_param_node(valid_value):
        pass

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(wrong_param_node)


def test_parametrized_single_param_breaks_without_docs():
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        function_modifiers.parametrized(
            parameter='parameter',
            assigned_output={'only_node_name': 'only_value'}
        )


def test_parametrized_single_param():
    annotation = function_modifiers.parametrized(
        parameter='parameter',
        assigned_output={('only_node_name', 'only_doc'): 'only_value'}
    )

    def identity(parameter: Any) -> Any:
        return parameter

    nodes = annotation.expand_node(node.Node.from_fn(identity), {}, identity)
    assert len(nodes) == 1
    assert nodes[0].name == 'only_node_name'
    assert nodes[0].type == Any
    assert nodes[0].documentation == 'only_doc'
    called = nodes[0].callable()
    assert called == 'only_value'


def test_parametrized_single_param_expanded():
    annotation = function_modifiers.parametrized(
        parameter='parameter',
        assigned_output={
            ('node_name_1', 'doc1'): 'value_1',
            ('node_value_2', 'doc2'): 'value_2'})

    def identity(parameter: Any) -> Any:
        return parameter

    nodes = annotation.expand_node(node.Node.from_fn(identity), {}, identity)
    assert len(nodes) == 2
    called_1 = nodes[0].callable()
    called_2 = nodes[1].callable()
    assert nodes[0].documentation == 'doc1'
    assert nodes[1].documentation == 'doc2'
    assert called_1 == 'value_1'
    assert called_2 == 'value_2'


def test_parametrized_with_multiple_params():
    annotation = function_modifiers.parametrized(
        parameter='parameter',
        assigned_output={
            ('node_name_1', 'doc1'): 'value_1',
            ('node_value_2', 'doc2'): 'value_2'})

    def identity(parameter: Any, static: Any) -> Any:
        return parameter, static

    nodes = annotation.expand_node(node.Node.from_fn(identity), {}, identity)
    assert len(nodes) == 2
    called_1 = nodes[0].callable(static='static_param')
    called_2 = nodes[1].callable(static='static_param')
    assert called_1 == ('value_1', 'static_param')
    assert called_2 == ('value_2', 'static_param')


def test_parametrized_input():
    annotation = function_modifiers.parametrized_input(
        parameter='parameter',
        variable_inputs={
            'input_1': ('test_1', 'Function with first column as input'),
            'input_2': ('test_2', 'Function with second column as input')
        })

    def identity(parameter: Any, static: Any) -> Any:
        return parameter, static

    nodes = annotation.expand_node(node.Node.from_fn(identity), {}, identity)
    assert len(nodes) == 2
    nodes = sorted(nodes, key=lambda n: n.name)
    assert [n.name for n in nodes] == ['test_1', 'test_2']
    assert set(nodes[0].input_types.keys()) == {'static', 'input_1'}
    assert set(nodes[1].input_types.keys()) == {'static', 'input_2'}


def test_parametrized_inputs_validate_param_name():
    """Tests validate function of parameterized_inputs capturing bad param name usage."""
    annotation = function_modifiers.parameterized_inputs(
        parameterization={
            'test_1': dict(parameterfoo='input_1'),
        })
    def identity(parameter1: str, parameter2: str, static: str) -> str:
        """Function with {parameter1} as first input"""
        return parameter1 + parameter2 + static

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(identity)


def test_parametrized_inputs_validate_reserved_param():
    """Tests validate function of parameterized_inputs catching reserved param usage."""
    annotation = function_modifiers.parameterized_inputs(
        **{
            'test_1': dict(parameter2='input_1'),
        })
    def identity(output_name: str, parameter2: str, static: str) -> str:
        """Function with {parameter2} as second input"""
        return output_name + parameter2 + static

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(identity)


def test_parametrized_inputs_validate_bad_doc_string():
    """Tests validate function of parameterized_inputs catching bad doc string."""
    annotation = function_modifiers.parameterized_inputs(
        **{
            'test_1': dict(parameter2='input_1'),
        })
    def identity(output_name: str, parameter2: str, static: str) -> str:
        """Function with {foo} as second input"""
        return output_name + parameter2 + static

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(identity)


def test_parametrized_inputs():
    annotation = function_modifiers.parameterized_inputs(
        **{
            'test_1': dict(parameter1='input_1', parameter2='input_2'),
            'test_2': dict(parameter1='input_2', parameter2='input_1'),
        })

    def identity(parameter1: str, parameter2: str, static: str) -> str:
        """Function with {parameter1} as first input"""
        return parameter1 + parameter2 + static

    nodes = annotation.expand_node(node.Node.from_fn(identity), {}, identity)
    assert len(nodes) == 2
    nodes = sorted(nodes, key=lambda n: n.name)
    assert [n.name for n in nodes] == ['test_1', 'test_2']
    assert set(nodes[0].input_types.keys()) == {'static', 'input_1', 'input_2'}
    assert nodes[0].documentation == 'Function with input_1 as first input'
    assert set(nodes[1].input_types.keys()) == {'static', 'input_1', 'input_2'}
    assert nodes[1].documentation == 'Function with input_2 as first input'
    result1 = nodes[0].callable(**{'input_1': '1', 'input_2': '2', 'static': '3'})
    assert result1 == '123'
    result2 = nodes[1].callable(**{'input_1': '1', 'input_2': '2', 'static': '3'})
    assert result2 == '213'


def test_invalid_column_extractor():
    annotation = function_modifiers.extract_columns('dummy_column')

    def no_param_node() -> int:
        pass

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(no_param_node)


def test_extract_columns_invalid_passing_list_to_column_extractor():
    """Ensures that people cannot pass in a list."""
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        function_modifiers.extract_columns(['a', 'b', 'c'])


def test_extract_columns_empty_args():
    """Tests that we fail on empty arguments."""
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        function_modifiers.extract_columns()


def test_extract_columns_happy():
    """Tests that we are happy with good arguments."""
    function_modifiers.extract_columns(*['a', ('b', 'some doc'), 'c'])


def test_valid_column_extractor():
    """Tests that things work, and that you can provide optional documentation."""
    annotation = function_modifiers.extract_columns('col_1', ('col_2', 'col2_doc'))

    def dummy_df_generator() -> pd.DataFrame:
        """dummy doc"""
        return pd.DataFrame({
            'col_1': [1, 2, 3, 4],
            'col_2': [11, 12, 13, 14]})

    nodes = list(annotation.expand_node(node.Node.from_fn(dummy_df_generator), {}, dummy_df_generator))
    assert len(nodes) == 3
    assert nodes[0] == node.Node(name=dummy_df_generator.__name__,
                                 typ=pd.DataFrame,
                                 doc_string=dummy_df_generator.__doc__,
                                 callabl=dummy_df_generator,
                                 tags={'module': 'tests.test_function_modifiers'})
    assert nodes[1].name == 'col_1'
    assert nodes[1].type == pd.Series
    assert nodes[1].documentation == 'dummy doc'  # we default to base function doc.
    assert nodes[1].input_types == {dummy_df_generator.__name__: (pd.DataFrame, DependencyType.REQUIRED)}
    assert nodes[2].name == 'col_2'
    assert nodes[2].type == pd.Series
    assert nodes[2].documentation == 'col2_doc'
    assert nodes[2].input_types == {dummy_df_generator.__name__: (pd.DataFrame, DependencyType.REQUIRED)}


def test_column_extractor_fill_with():
    def dummy_df() -> pd.DataFrame:
        """dummy doc"""
        return pd.DataFrame({
            'col_1': [1, 2, 3, 4],
            'col_2': [11, 12, 13, 14]})

    annotation = function_modifiers.extract_columns('col_3', fill_with=0)
    original_node, extracted_column_node = annotation.expand_node(node.Node.from_fn(dummy_df), {}, dummy_df)
    original_df = original_node.callable()
    extracted_column = extracted_column_node.callable(dummy_df=original_df)
    pd.testing.assert_series_equal(extracted_column, pd.Series([0, 0, 0, 0]), check_names=False)
    pd.testing.assert_series_equal(original_df['col_3'], pd.Series([0, 0, 0, 0]), check_names=False)  # it has to be in there now


def test_column_extractor_no_fill_with():
    def dummy_df_generator() -> pd.DataFrame:
        """dummy doc"""
        return pd.DataFrame({
            'col_1': [1, 2, 3, 4],
            'col_2': [11, 12, 13, 14]})

    annotation = function_modifiers.extract_columns('col_3')
    nodes = list(annotation.expand_node(node.Node.from_fn(dummy_df_generator), {}, dummy_df_generator))
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        nodes[1].callable(dummy_df_generator=dummy_df_generator())


def test_no_code_validator():
    def no_code():
        pass

    def no_code_with_docstring():
        """This should still show up as having no code, even though it has a docstring"""
        pass

    def yes_code():
        """This should show up as having no code"""
        a = 0
        return a

    ensure_function_empty(no_code)
    ensure_function_empty(no_code_with_docstring)
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        ensure_function_empty(yes_code)


def test_fn_kwarg_only_validator():
    def kwarg_only(**kwargs):
        pass

    def more_args(param1, param2, *args, **kwargs):
        pass

    def kwargs_and_args(*args, **kwargs):
        pass

    def args_only(*args):
        pass

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        does.ensure_function_kwarg_only(more_args)

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        does.ensure_function_kwarg_only(kwargs_and_args)

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        does.ensure_function_kwarg_only(args_only)

    does.ensure_function_kwarg_only(kwarg_only)


def test_compatible_return_types():
    def returns_int() -> int:
        return 0

    def returns_str() -> str:
        return 'zero'

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        does.ensure_output_types_match(returns_int, returns_str)

    does.ensure_output_types_match(returns_int, returns_int)


def test_does_function_modifier():
    def sum_(**kwargs: int) -> int:
        return sum(kwargs.values())

    def to_modify(param1: int, param2: int) -> int:
        """This sums the inputs it gets..."""
        pass

    annotation = does(sum_)
    node = annotation.generate_node(to_modify, {})
    assert node.name == 'to_modify'
    assert node.callable(param1=1, param2=1) == 2
    assert node.documentation == to_modify.__doc__


def test_model_modifier():
    config = {
        'my_column_model_params': {
            'col_1': .5,
            'col_2': .5,
        }
    }

    class LinearCombination(models.BaseModel):
        def get_dependents(self) -> List[str]:
            return list(self.config_parameters.keys())

        def predict(self, **columns: pd.Series) -> pd.Series:
            return sum(self.config_parameters[column_name] * column for column_name, column in columns.items())

    def my_column() -> pd.Series:
        """Column that will be annotated by a model"""
        pass

    annotation = function_modifiers.model(LinearCombination, 'my_column_model_params')
    annotation.validate(my_column)
    model_node = annotation.generate_node(my_column, config)
    assert model_node.input_types['col_1'][0] == model_node.input_types['col_2'][0] == pd.Series
    assert model_node.type == pd.Series
    pd.testing.assert_series_equal(model_node.callable(col_1=pd.Series([1]), col_2=pd.Series([2])), pd.Series([1.5]))

    def bad_model(col_1: pd.Series, col_2: pd.Series) -> pd.Series:
        return col_1 * .5 + col_2 * .5

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(bad_model)


def test_sanitize_function_name():
    assert function_modifiers_base.sanitize_function_name('fn_name__v2') == 'fn_name'
    assert function_modifiers_base.sanitize_function_name('fn_name') == 'fn_name'


def test_config_modifier_validate():
    def valid_fn() -> int:
        pass

    def valid_fn__this_is_also_valid() -> int:
        pass

    function_modifiers.config.when(key='value').validate(valid_fn__this_is_also_valid)
    function_modifiers.config.when(key='value').validate(valid_fn)

    def invalid_function__() -> int:
        pass

    with pytest.raises(function_modifiers.InvalidDecoratorException):
        function_modifiers.config.when(key='value').validate(invalid_function__)


def test_config_when():
    def config_when_fn() -> int:
        pass

    annotation = function_modifiers.config.when(key='value')
    assert annotation.resolve(config_when_fn, {'key': 'value'}) is not None
    assert annotation.resolve(config_when_fn, {'key': 'wrong_value'}) is None


def test_config_when_not():
    def config_when_not_fn() -> int:
        pass

    annotation = function_modifiers.config.when_not(key='value')
    assert annotation.resolve(config_when_not_fn, {'key': 'other_value'}) is not None
    assert annotation.resolve(config_when_not_fn, {'key': 'value'}) is None


def test_config_when_in():
    def config_when_in_fn() -> int:
        pass

    annotation = function_modifiers.config.when_in(key=['valid_value', 'another_valid_value'])
    assert annotation.resolve(config_when_in_fn, {'key': 'valid_value'}) is not None
    assert annotation.resolve(config_when_in_fn, {'key': 'another_valid_value'}) is not None
    assert annotation.resolve(config_when_in_fn, {'key': 'not_a_valid_value'}) is None


def test_config_when_not_in():
    def config_when_not_in_fn() -> int:
        pass

    annotation = function_modifiers.config.when_not_in(key=['invalid_value', 'another_invalid_value'])
    assert annotation.resolve(config_when_not_in_fn, {'key': 'invalid_value'}) is None
    assert annotation.resolve(config_when_not_in_fn, {'key': 'another_invalid_value'}) is None
    assert annotation.resolve(config_when_not_in_fn, {'key': 'valid_value'}) is not None


def test_config_name_resolution():
    def fn__v2() -> int:
        pass

    annotation = function_modifiers.config.when(key='value')
    assert annotation.resolve(fn__v2, {'key': 'value'}).__name__ == 'fn'


def test_config_when_with_custom_name():
    def config_when_fn() -> int:
        pass

    annotation = function_modifiers.config.when(key='value', name='new_function_name')
    assert annotation.resolve(config_when_fn, {'key': 'value'}).__name__ == 'new_function_name'


@pytest.mark.parametrize('fields', [
    (None),  # empty
    ('string_input'),  # not a dict
    (['string_input']),  # not a dict
    ({}),  # empty dict
    ({1: 'string', 'field': str}),  # invalid dict
    ({'field': lambda x: x, 'field2': int}),  # invalid dict
])
def test_extract_fields_constructor_errors(fields):
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        function_modifiers.extract_fields(fields)


@pytest.mark.parametrize('fields', [
    ({'field': np.ndarray, 'field2': str}),
    ({'field': dict, 'field2': int, 'field3': list, 'field4': float, 'field5': str}),
])
def test_extract_fields_constructor_happy(fields):
    """Tests that we are happy with good arguments."""
    function_modifiers.extract_fields(fields)


@pytest.mark.parametrize('return_type', [
    (dict),
    (Dict),
    (Dict[str, str]),
    (Dict[str, Any]),
])
def test_extract_fields_validate_happy(return_type):
    def return_dict() -> return_type:
        return {}

    annotation = function_modifiers.extract_fields({'test': int})
    annotation.validate(return_dict)


@pytest.mark.parametrize('return_type', [
    (int), (list), (np.ndarray), (pd.DataFrame)
])
def test_extract_fields_validate_errors(return_type):
    def return_dict() -> return_type:
        return {}

    annotation = function_modifiers.extract_fields({'test': int})
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        annotation.validate(return_dict)


def test_valid_extract_fields():
    """Tests whole extract_fields decorator."""
    annotation = function_modifiers.extract_fields({'col_1': list, 'col_2': int, 'col_3': np.ndarray})

    def dummy_dict_generator() -> dict:
        """dummy doc"""
        return {'col_1': [1, 2, 3, 4],
                'col_2': 1,
                'col_3': np.ndarray([1, 2, 3, 4])}

    nodes = list(annotation.expand_node(node.Node.from_fn(dummy_dict_generator), {}, dummy_dict_generator))
    assert len(nodes) == 4
    assert nodes[0] == node.Node(name=dummy_dict_generator.__name__,
                                 typ=dict,
                                 doc_string=dummy_dict_generator.__doc__,
                                 callabl=dummy_dict_generator,
                                 tags={'module': 'tests.test_function_modifiers'})
    assert nodes[1].name == 'col_1'
    assert nodes[1].type == list
    assert nodes[1].documentation == 'dummy doc'  # we default to base function doc.
    assert nodes[1].input_types == {dummy_dict_generator.__name__: (dict, DependencyType.REQUIRED)}
    assert nodes[2].name == 'col_2'
    assert nodes[2].type == int
    assert nodes[2].documentation == 'dummy doc'
    assert nodes[2].input_types == {dummy_dict_generator.__name__: (dict, DependencyType.REQUIRED)}
    assert nodes[3].name == 'col_3'
    assert nodes[3].type == np.ndarray
    assert nodes[3].documentation == 'dummy doc'
    assert nodes[3].input_types == {dummy_dict_generator.__name__: (dict, DependencyType.REQUIRED)}


def test_extract_fields_fill_with():
    def dummy_dict() -> dict:
        """dummy doc"""
        return {'col_1': [1, 2, 3, 4],
                'col_2': 1,
                'col_3': np.ndarray([1, 2, 3, 4])}

    annotation = function_modifiers.extract_fields({'col_2': int, 'col_4': float}, fill_with=1.0)
    original_node, extracted_field_node, missing_field_node = annotation.expand_node(node.Node.from_fn(dummy_dict),
                                                                                     {},
                                                                                     dummy_dict)
    original_dict = original_node.callable()
    extracted_field = extracted_field_node.callable(dummy_dict=original_dict)
    missing_field = missing_field_node.callable(dummy_dict=original_dict)
    assert extracted_field == 1
    assert missing_field == 1.0


def test_extract_fields_no_fill_with():
    def dummy_dict() -> dict:
        """dummy doc"""
        return {'col_1': [1, 2, 3, 4],
                'col_2': 1,
                'col_3': np.ndarray([1, 2, 3, 4])}

    annotation = function_modifiers.extract_fields({'col_4': int})
    nodes = list(annotation.expand_node(node.Node.from_fn(dummy_dict), {}, dummy_dict))
    with pytest.raises(function_modifiers.InvalidDecoratorException):
        nodes[1].callable(dummy_dict=dummy_dict())


def test_tags():
    def dummy_tagged_function() -> int:
        """dummy doc"""
        return 1

    annotation = function_modifiers.tag(foo='bar', bar='baz')
    node_ = annotation.decorate_node(node.Node.from_fn(dummy_tagged_function))
    assert 'foo' in node_.tags
    assert 'bar' in node_.tags


@pytest.mark.parametrize(
    'key',
    [
        'hamilton',  # Reserved key
        'foo@',  # Invalid identifier
        'foo bar',  # No spaces
        'foo.bar+baz',  # Invalid key, not a valid identifier
        ''  # Empty not allowed
        '...'  # Empty elements not allowed
    ]
)
def test_tags_invalid_key(key):
    assert not function_modifiers.tag._key_allowed(key)


@pytest.mark.parametrize(
    'key',
    [
        'bar.foo',
        'foo',  # Invalid identifier
        'foo.bar.baz',  # Invalid key, not a valid identifier
    ]
)
def test_tags_valid_key(key):
    assert function_modifiers.tag._key_allowed(key)


@pytest.mark.parametrize(
    'value',
    [
        None,
        False,
        [],
        ['foo', 'bar']
    ]
)
def test_tags_invalid_value(value):
    assert not function_modifiers.tag._value_allowed(value)


@pytest.mark.parametrize(
    'value',
    [
        None,
        False,
        [],
        ['foo', 'bar']
    ]
)
def test_tags_invalid_value(value):
    assert not function_modifiers.tag._value_allowed(value)
