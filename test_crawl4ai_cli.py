#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from click.testing import CliRunner
from pathlib import Path
import json
import yaml
from crawl4ai.cli import cli, load_config_file, parse_key_values
import tempfile
import os
import click

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def temp_config_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_home = os.environ.get('HOME')
        os.environ['HOME'] = tmpdir
        yield Path(tmpdir)
        if old_home:
            os.environ['HOME'] = old_home

@pytest.fixture
def sample_configs(temp_config_dir):
    configs = {
        'browser.yml': {
            'headless': True,
            'viewport_width': 1280,
            'user_agent_mode': 'random'
        },
        'crawler.yml': {
            'cache_mode': 'bypass',
            'wait_until': 'networkidle',
            'scan_full_page': True
        },
        'extract_css.yml': {
            'type': 'json-css',
            'params': {'verbose': True}
        },
        'css_schema.json': {
            'name': 'ArticleExtractor',
            'baseSelector': '.article',
            'fields': [
                {'name': 'title', 'selector': 'h1.title', 'type': 'text'},
                {'name': 'link', 'selector': 'a.read-more', 'type': 'attribute', 'attribute': 'href'}
            ]
        }
    }
    
    for filename, content in configs.items():
        path = temp_config_dir / filename
        with open(path, 'w') as f:
            if filename.endswith('.yml'):
                yaml.dump(content, f)
            else:
                json.dump(content, f)
                
    return {name: str(temp_config_dir / name) for name in configs}

class TestCLIBasics:
    def test_help(self, runner):
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Crawl4AI CLI' in result.output

    def test_examples(self, runner):
        result = runner.invoke(cli, ['--example'])
        assert result.exit_code == 0
        assert 'Examples' in result.output

    def test_missing_url(self, runner):
        result = runner.invoke(cli)
        assert result.exit_code != 0
        assert 'URL argument is required' in result.output

class TestConfigParsing:
    def test_parse_key_values_basic(self):
        result = parse_key_values(None, None, "key1=value1,key2=true")
        assert result == {'key1': 'value1', 'key2': True}

    def test_parse_key_values_numbers(self):
        result = parse_key_values(None, None, "int_val=42,float_val=3.14")
        assert result == {'int_val': 42, 'float_val': 3.14}
        
    def test_parse_key_values_booleans(self):
        result = parse_key_values(None, None, "true_val=true,false_val=false")
        assert result == {'true_val': True, 'false_val': False}

    def test_parse_key_values_invalid(self):
        with pytest.raises(click.BadParameter):
            parse_key_values(None, None, "invalid_format")

class TestConfigLoading:
    def test_load_yaml_config(self, sample_configs):
        config = load_config_file(sample_configs['browser.yml'])
        assert config['headless'] is True
        assert config['viewport_width'] == 1280

    def test_load_json_config(self, sample_configs):
        config = load_config_file(sample_configs['css_schema.json'])
        assert config['name'] == 'ArticleExtractor'
        assert len(config['fields']) == 2

    def test_load_nonexistent_config(self):
        with pytest.raises(click.BadParameter):
            load_config_file('nonexistent.yml')

class TestLLMConfig:
    def test_llm_config_creation(self, temp_config_dir, runner):
        # Simulated user input for LLM configuration
        inputs = [
            'openai',  # LLM provider
            'gpt-4o',  # Model name
            '',  # Default API base
            'test-api-key',  # API key
            'y'  # Save config
        ]
        
        result = runner.invoke(cli, ['https://example.com', '-q', 'test question'], 
                             input='\n'.join(inputs))
        
        assert result.exit_code == 0
        
        # Check if config was created
        config_path = temp_config_dir / '.crawl4ai' / 'llm_config.yml'
        assert config_path.exists()
        
        # Verify config contents
        with open(config_path) as f:
            config = yaml.safe_load(f)
            assert config['provider'] == 'openai'
            assert config['model'] == 'gpt-4o'
            assert 'api_key' in config

class TestCrawlingFeatures:
    def test_basic_crawl(self, runner, monkeypatch):
        # Mock the crawling functionality to avoid actual web requests
        # during testing
        def mock_crawl(*args, **kwargs):
            return {
                'success': True,
                'page_title': 'Example Domain',
                'html_content': '<html><body><h1>Example Domain</h1></body></html>'
            }
        
        monkeypatch.setattr('crawl4ai.cli.perform_crawl', mock_crawl)
        
        result = runner.invoke(cli, ['https://example.com'])
        assert result.exit_code == 0
        assert 'Successfully crawled' in result.output

    def test_crawl_with_extraction(self, runner, monkeypatch, sample_configs):
        # Mock extraction results
        def mock_crawl_with_extraction(*args, **kwargs):
            return {
                'success': True,
                'page_title': 'Example Domain',
                'extracted_content': json.dumps([
                    {'title': 'Test Article', 'link': 'https://example.com/test'}
                ])
            }
        
        monkeypatch.setattr('crawl4ai.cli.perform_crawl', mock_crawl_with_extraction)
        
        result = runner.invoke(cli, [
            'https://example.com',
            '--schema', sample_configs['css_schema.json']
        ])
        
        assert result.exit_code == 0
        assert 'Extracted content:' in result.output
        assert 'Test Article' in result.output

class TestErrorHandling:
    def test_invalid_config_file(self, runner):
        result = runner.invoke(cli, [
            'https://example.com',
            '--browser-config', 'nonexistent.yml'
        ])
        assert result.exit_code != 0
        assert 'Could not find config file' in result.output

    def test_invalid_schema(self, runner, temp_config_dir):
        invalid_schema = temp_config_dir / 'invalid_schema.json'
        with open(invalid_schema, 'w') as f:
            f.write('invalid json')
            
        result = runner.invoke(cli, [
            'https://example.com',
            '--schema', str(invalid_schema)
        ])
        assert result.exit_code != 0
        assert 'Error loading schema' in result.output

    def test_crawl_failure(self, runner, monkeypatch):
        # Mock a failed crawl
        def mock_failed_crawl(*args, **kwargs):
            return {
                'success': False,
                'error_message': 'Connection timeout'
            }
        
        monkeypatch.setattr('crawl4ai.cli.perform_crawl', mock_failed_crawl)
        
        result = runner.invoke(cli, ['https://example.com'])
        assert result.exit_code != 0
        assert 'Failed to crawl' in result.output
        assert 'Connection timeout' in result.output

class TestOutputFormats:
    def test_json_output(self, runner, monkeypatch, temp_config_dir):
        # Mock successful crawl with content
        def mock_crawl(*args, **kwargs):
            return {
                'success': True,
                'page_title': 'Test Page',
                'html_content': '<html><body><h1>Test</h1></body></html>',
                'url': 'https://example.com'
            }
        
        monkeypatch.setattr('crawl4ai.cli.perform_crawl', mock_crawl)
        
        output_file = temp_config_dir / 'output.json'
        
        result = runner.invoke(cli, [
            'https://example.com',
            '--output', str(output_file),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        
        with open(output_file) as f:
            content = json.load(f)
            assert content['success'] is True
            assert content['page_title'] == 'Test Page'

if __name__ == '__main__':
    pytest.main(['-v', '-s', '--tb=native', __file__]) 